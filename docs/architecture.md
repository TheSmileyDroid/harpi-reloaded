# Arquitetura

Referência: [Arquitetura Limpa (Engenharia de Software Moderna)](https://engsoftmoderna.info/artigos/arquitetura-limpa.html)

A regra central da Arquitetura Limpa: camadas internas nunca conhecem classes de camadas externas. Quando uma classe interna precisa de algo externo (tocar áudio, resolver metadados, etc.), ela depende de uma **porta** (interface) definida em camada interna, e é a camada externa que implementa essa porta.

---

## Domain (Entidades)

Classes de dados e regras de negócio, livres de qualquer tecnologia: nenhum import externo, nem de framework. É a camada onde os testes de unidade e o teste de mutação se concentram.

- **TrackMetadata**: Valor imutável (`frozen dataclass`) com os metadados de uma música (título, duração, link, origem). Deriva `source_id` a partir do link conforme a origem.
- **BackgroundTrackId**: Value object (wrapper sobre UUID) que identifica de forma única cada entrada de áudio de fundo.
- **LoopMode**: Enum com os modos de loop (`TRACK`, `QUEUE`, `OFF`).
- **Volume**: `validate_volume()` e constantes `MIN_VOLUME`/`MAX_VOLUME`. Regra de validação da faixa 0.0 a 1.0, testada com Análise de Valor Limite.
- **Queue**: Fila de músicas (`TrackMetadata`). Controla adição e remoção e decide a próxima música conforme o `LoopMode`. É a regra de negócio mais rica do sistema.
- **Background**: Coleção de `BackgroundEntry` (id + metadados + loop próprio). Gerencia os áudios de fundo com identidade por `BackgroundTrackId`.
- **Guild**: Agregado do estado de um servidor Discord: mantém a `Queue` e o `Background` daquele servidor.

> **Nota:** `Queue`, `Guild` e `Background` moram no Domain porque são livres de tecnologia e expressam regras de negócio próprias (looping, identidade, agregação por servidor). A orquestração dessas entidades com o mundo externo (essa sim específica da aplicação) fica no `PlayerService`, na camada de Application.

---

## Application (Casos de Uso)

Orquestra as Entidades e aciona as Portas. Depende apenas do Domain, nunca de infraestrutura.

### Portas (Interfaces)

Definidas em `application/ports/` como `Protocol` para que os casos de uso acionem funcionalidades externas sem violar a Regra de Dependência. Implementadas pelos Adaptadores e, nos testes de unidade, por fakes escritos à mão (`FakeResolver`, `FakePlayer`).

- **AudioResolverProtocol**: `resolve(link) -> TrackMetadata` e `resolve_stream(track) -> str`. Abstrai a resolução de metadados e de URL de stream a partir de uma fonte (YouTube, etc.).
- **AudioPlayerProtocol**: Abstrai o playback no canal de voz (`play`, `pause`, `resume`, `stop`, volumes, ducking, background sources), de modo que os Casos de Uso não conhecem `DiscordPlayer`.

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
```

### Classes

- **PlayerService**: Orquestrador central. Recebe as portas por injeção de dependência. Coordena fila, playback, volumes, ducking e o encadeamento de faixas (`on_track_end` decide a próxima conforme o `LoopMode`).
- **TrackFactory**: Chama `AudioResolverProtocol.resolve()` e devolve `TrackMetadata`. Separa a resolução de links da orquestração de playback.
- **Commands** (`application/commands/`): Um arquivo por comando (`play`, `skip`, `pause`, `resume`, `stop`, `volume`, `loop`, `rm`, `queue`, `background_*`). Funções async registradas via decorator `@register("nome")` num registry; cada handler recebe o `PlayerService` e os argumentos e devolve `str` ou `EmbedData`.
- **Exceptions**: Exceções da aplicação (`InvalidLinkError`, `NetworkError`, `ResolutionTimeoutError`), que os adaptadores traduzem a partir de erros de bibliotecas externas.

---

## Adapters (Infrastructure)

Traduzem entre o mundo externo (Discord, FFmpeg, pytubefix, numpy) e as camadas internas. Implementam as Portas. Todo acoplamento a framework fica confinado aqui.

- **YoutubeResolver**: Implementa `AudioResolverProtocol`. Extrai metadados via `pytubefix` e traduz os erros da biblioteca para as exceções da aplicação.
- **DiscordPlayer**: Implementa `AudioPlayerProtocol`. Resolve a URL de stream, cria os subprocessos FFmpeg (PCM s16le 48kHz estéreo) e envia o áudio ao canal de voz via `discord.py`. Controla pausa, posição, volumes e ducking.
- **MixedAudioSource**: `discord.AudioSource` que mescla múltiplos streams PCM (faixa principal e fundos) com numpy, aplicando os fatores de volume por source. Toda a mixagem do sistema acontece nessa classe.
- **CommandRouter**: Faz o parse das mensagens (prefixo `-`), consulta o registry de comandos e despacha para o handler. Gera o `-help` a partir do registry.
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

Essa regra é o que permite a estratégia de testes do projeto: o Domain e a Application são testados por completo com fakes (sem IO, sem mocks de framework), e os Adapters são verificados por testes de integração contra os serviços reais.

---

## Estrutura de arquivos

```
src/harpi/
├── domain/                          # Entidades, zero dependências
│   ├── track_metadata.py            # TrackMetadata (+ Source)
│   ├── background_track_id.py       # Value object (wrapper sobre UUID)
│   ├── background.py                # Background + BackgroundEntry
│   ├── guild.py                     # Guild (Queue + Background por servidor)
│   ├── loop_mode.py                 # LoopMode (TRACK, QUEUE, OFF)
│   ├── queue.py                     # Queue (fila + regras de looping)
│   └── volume.py                    # validate_volume(), MIN_VOLUME, MAX_VOLUME
├── application/                     # Casos de Uso, define Portas
│   ├── player_service.py            # Orquestrador central
│   ├── track_factory.py             # AudioResolverProtocol -> TrackMetadata
│   ├── exceptions.py                # Exceções da aplicação
│   ├── ports/
│   │   └── audio.py                 # AudioResolverProtocol, AudioPlayerProtocol
│   └── commands/                    # Um arquivo por comando
│       ├── __init__.py              # Registry (@register) + EmbedData/Response
│       ├── play.py ... stop.py      # play, skip, pause, resume, stop
│       ├── volume.py, loop.py, rm.py, queue.py
│       └── background_add.py, background_remove.py, background_set.py
└── infrastructure/                  # Adaptadores, implementam Portas
    ├── youtube_resolver.py          # Implementa AudioResolverProtocol
    ├── discord_player.py            # Implementa AudioPlayerProtocol
    ├── mixed_audio_source.py        # Mixagem PCM via numpy (discord.AudioSource)
    ├── command_router.py            # Mensagens -> Commands
    └── discord_bot.py               # HarpiBot, composition root
main.py                              # Entry point
```

---

## Evolução planejada

Refinos já mapeados, não necessários para a corretude atual:

- **CompositeSourceResolver** (SMI-25): agregador de resolvers para múltiplas fontes. Só ganha valor quando houver um segundo resolver concreto (SpotifyResolver, SMI-6). Hoje seria generalidade especulativa sobre um único `YoutubeResolver`.
- **FFmpegSource + Mixer puro** (SMI-23/24): separar o `MixedAudioSource` em um source FFmpeg reutilizável e um mixer numpy independente de `discord.py`, o que permitiria testar a mixagem em unidade.
