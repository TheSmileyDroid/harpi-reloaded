# Arquitetura

Referência: [Arquitetura Limpa (Engenharia de Software Moderna)](https://engsoftmoderna.info/artigos/arquitetura-limpa.html)

A regra central: camadas internas nunca conhecem classes de camadas externas. Quando uma classe interna precisa de algo externo (tocar áudio, resolver metadados, etc.), ela depende de uma **porta** (interface) definida na camada interna, e é a camada externa que implementa essa porta.

---

## Domain (Entidades)

Classes de dados e regras de negócio, sem import externo nem dependência de framework. É onde os testes de unidade e o teste de mutação se concentram.

- **TrackMetadata**: Valor imutável (`frozen dataclass`) com metadados de uma música (título, duração, link, origem). Deriva `source_id` a partir do link conforme a origem.
- **LoopMode**: Enum com os modos de loop (`TRACK`, `QUEUE`, `OFF`).
- **Volume**: `validate_volume()` e constantes `MIN_VOLUME`/`MAX_VOLUME`. Faixa válida: 0.0 a 1.0, testada com Análise de Valor Limite.
- **Queue**: Fila de músicas (`TrackMetadata`). Controla adição, remoção e decide a próxima música conforme o `LoopMode`. Também gerencia os áudios de fundo (lista interna de `TrackMetadata`).

---

## Application (Casos de Uso)

Orquestra as Entidades e aciona as Portas. Depende apenas do Domain.

### Portas (Interfaces)

Definidas em `application/ports/audio.py` como `Protocol`. Os adaptadores as implementam, nos testes de unidade, fakes escritos à mão (`FakeResolver`, `FakePlayer`) cumprem o mesmo contrato.

- **AudioResolverProtocol**: `resolve(link) -> TrackMetadata` e `resolve_stream(track) -> str`. Resolução de metadados e URL de stream a partir de uma fonte (YouTube, etc.).
- **AudioPlayerProtocol**: Playback no canal de voz (`play`, `pause`, `resume`, `stop`, volumes, ducking, background sources). Os casos de uso não conhecem `DiscordPlayer`.
- **AudioPlayerFactoryProtocol**: `create_player(resolver) -> AudioPlayerProtocol`. Cria instâncias de player por guild.

```python
class AudioResolverProtocol(Protocol):
    async def resolve(self, link: str) -> TrackMetadata: ...
    async def resolve_stream(self, track: TrackMetadata) -> str: ...

class AudioPlayerProtocol(Protocol):
    async def play(self, track: TrackMetadata, on_finish=None) -> None: ...
    async def pause(self) -> None: ...
    async def resume(self) -> None: ...
    async def stop(self) -> None: ...
    # ... demais métodos e propriedades

class AudioPlayerFactoryProtocol(Protocol):
    def create_player(self, resolver: AudioResolverProtocol) -> AudioPlayerProtocol: ...
```

### Classes

- **PlayerService**: Orquestrador central. Recebe as portas por injeção de dependência. Coordena fila, playback, volumes, ducking e encadeamento de faixas (`on_track_end` decide a próxima conforme o `LoopMode`).
- **Commands** (`application/commands/`): Um arquivo por comando. Funções async registradas via decorator `@register("nome")` num registry; cada handler recebe o `PlayerService` e os argumentos e devolve `str` ou `EmbedData`.
- **Exceptions** (`exceptions.py`): `ResolutionError` (base), `InvalidLinkError`, `NetworkError`, `ResolutionTimeoutError`. Os adaptadores traduzem erros de bibliotecas externas para essas exceções.

---

## Adapters (Infrastructure)

Traduzem entre o mundo externo (Discord, FFmpeg, pytubefix, numpy) e as camadas internas. Implementam as Portas. Todo acoplamento a framework fica confinado aqui.

- **YoutubeResolver**: Implementa `AudioResolverProtocol`. Extrai metadados via `pytubefix` e traduz os erros da biblioteca para as exceções da aplicação.
- **DiscordPlayer**: Implementa `AudioPlayerProtocol`. Recebe um `AudioResolverProtocol` por injeção e chama `resolve_stream()` para obter a URL de áudio. Cria subprocessos FFmpeg (PCM s16le 48kHz estéreo), envia o áudio ao canal de voz via `discord.py` e controla pausa, posição, volumes e ducking.
- **DiscordPlayerFactory**: Implementa `AudioPlayerFactoryProtocol`. Instancia `DiscordPlayer` com o resolver injetado.
- **MixedAudioSource**: `discord.AudioSource` que mescla múltiplos streams PCM (faixa principal e fundos) com numpy, aplicando fatores de volume por source.
- **CommandRouter**: Parse das mensagens (prefixo `-`), consulta o registry de comandos e despacha para o handler. Gera o `-help` a partir do registry.
- **HarpiBot** (`discord_bot.py`): Composition root. Instancia as implementações concretas, injeta nas Portas, mantém o estado por servidor (um `PlayerService`/`CommandRouter` por guild) e garante a conexão de voz para comandos que exigem canal.

---

## Frameworks Externos / Main

- **main.py**: Entry point. Carrega configuração (token) e inicia o `HarpiBot`.

---

## Regra de Dependência

```
Frameworks Externos → Adapters → Application (Casos de Uso) → Domain (Entidades)
       ↑                  ↑               ↑                        ↑
  depende de         depende de      depende de              zero dependências
```

- **Domain**: zero dependências externas. Apenas dados e regras de negócio.
- **Application**: depende apenas de Domain. Define as Portas que precisa.
- **Adapters**: dependem de Application (implementam as Portas) e de Domain.
- **Frameworks Externos**: dependem de todos os anteriores. Instanciam e conectam tudo.

Essa regra permite a estratégia de testes: Domain e Application são testados com fakes (sem IO, sem mocks de framework). Adapters são verificados por testes de integração contra serviços reais.

---

## Estrutura de arquivos

```
src/harpi/
├── domain/                          # Entidades, zero dependências
│   ├── track_metadata.py            # TrackMetadata (+ Source)
│   ├── loop_mode.py                 # LoopMode (TRACK, QUEUE, OFF)
│   ├── queue.py                     # Queue (fila + background + regras de looping)
│   └── volume.py                    # validate_volume(), MIN_VOLUME, MAX_VOLUME
├── application/                     # Casos de Uso, define Portas
│   ├── player_service.py            # Orquestrador central
│   ├── exceptions.py                # ResolutionError, InvalidLinkError, etc.
│   ├── ports/
│   │   └── audio.py                 # AudioResolverProtocol, AudioPlayerProtocol, AudioPlayerFactoryProtocol
│   └── commands/                    # Um arquivo por comando
│       ├── __init__.py              # Registry (@register) + EmbedData/Response
│       ├── play.py ... stop.py      # play, skip, pause, resume, stop
│       ├── volume.py, loop.py, rm.py, queue.py
│       └── background_set.py, background_add.py, background_remove.py
└── infrastructure/                  # Adaptadores, implementam Portas
    ├── youtube_resolver.py          # Implementa AudioResolverProtocol
    ├── discord_player.py            # Implementa AudioPlayerProtocol
    ├── mixed_audio_source.py        # Mixagem PCM via numpy (discord.AudioSource)
    ├── command_router.py            # Mensagens -> Commands
    └── discord_bot.py               # HarpiBot, composition root
main.py                              # Entry point
```
