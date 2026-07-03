# Arquitetura

Referência: [Arquitetura Limpa — Engenharia de Software Moderna](https://engsoftmoderna.info/artigos/arquitetura-limpa.html)

A regra central da Arquitetura Limpa: camadas internas nunca conhecem classes de camadas externas. Quando uma classe interna precisa de algo externo (tocar áudio, resolver metadados, etc.), ela depende de uma **porta** (interface) definida na própria camada interna, e é a camada externa que implementa essa porta.

---

## Domain (Entidades)

Classes de dados + regras de negócio **genéricas**, reutilizáveis em outros sistemas. Livres de qualquer tecnologia.

- **TrackMetadata**: Representação dos metadados de uma música (título, duração, URL de origem, etc.).
- **BackgroundTrackId**: Value object (wrapper sobre UUID) que identifica de forma única cada entrada de áudio de fundo.
- **LoopMode**: Enum que define os modos de loop (`TRACK`, `QUEUE`, `OFF`).
- **Volume**: Função utilitária `validate_volume()` e constantes `MIN_VOLUME`/`MAX_VOLUME`. Regra de negócio genérica de validação de faixa 0.0–1.0.

> **Nota:** `Queue`, `Guild` e `Background` são **Casos de Uso** (ver abaixo), pois contêm regras específicas deste sistema (modos de loop por fila, gerenciamento de background por servidor, etc.).

---

## Application (Casos de Uso)

Regras de negócio **específicas** deste sistema. Orquestram as Entidades e chamam as Portas. Podem depender de Entidades, mas Entidades nunca dependem de Casos de Uso.

### Portas (Interfaces)

Definidas na camada de Casos de Uso para que os use cases possam acionar funcionalidades externas sem violar a Regra de Dependência. Implementadas pelos Adaptadores correspondentes.

- **AudioResolverProtocol**: `resolve(link) -> TrackMetadata`. Abstrai a resolução de metadados a partir de uma fonte (YouTube, Spotify, etc.). A estratégia que escolhe qual resolver usar para uma dada entrada é regra de negócio e deve operar sobre essa interface, não sobre classes concretas como `YoutubeResolver`.
- **AudioPlayerProtocol**: Abstrai o envio de áudio para o canal de voz e a conexão ao canal do usuário (`play`, `pause`, `connect`, `disconnect`), permitindo que os Casos de Uso não conheçam `DiscordPlayer` diretamente.

```python
class AudioResolverProtocol(Protocol):
    async def resolve(self, link: str) -> TrackMetadata: ...

class AudioPlayerProtocol(Protocol):
    async def play(self, track: TrackMetadata, on_finish: Callable[[], Awaitable[None]] | None = None) -> None: ...
    async def pause(self) -> None: ...
    async def resume(self) -> None: ...
    async def stop(self) -> None: ...
    # ... demais métodos e propriedades
```

### Classes

- **PlayerService**: Orquestrador central. Recebe as portas `AudioResolverProtocol` e `AudioPlayerProtocol` por injeção de dependência. Coordena a fila, o playback e o estado por servidor.
- **TrackFactory**: Chama `AudioResolverProtocol.resolve()` → retorna `TrackMetadata`. Separa a resolução de links da orquestração de playback.
- **Queue**: Fila de músicas (`TrackMetadata`) por servidor. Controla adição, remoção e qual a próxima música a tocar conforme o modo de looping.
- **Background**: Gerencia áudios de fundo por servidor. Cada entrada (`BackgroundEntry`) possui seu próprio modo de loop.
- **Guild**: Dados e estado do servidor; mantém a `Queue` e o `Background`.
- **Command**: Cada comando recebe o contexto da `Guild` e os argumentos, orquestra as Entidades e aciona as Portas.

---

## Adapters

Classes que traduzem entre o mundo externo (Discord, FFmpeg, yt-dlp, numpy) e as camadas internas. Implementam as Portas definidas na camada de Casos de Uso.

- **YoutubeResolver**: Implementa `AudioResolverProtocol`. Extrai metadados de uma música do YouTube. Adaptador para a biblioteca `pytubefix`.
- **CompositeSourceResolver**: Implementa `AudioResolverProtocol`. Agrega múltiplos resolvers concretos (YouTube, Spotify, etc.) e delega para o adequado.
- **DiscordPlayer**: Implementa `AudioPlayerProtocol`. Envia áudio para o canal de Discord conectado. Conecta-se ao canal do usuário caso necessário.
- **FFmpegSource**: Implementa uma abstração de source de áudio via subprocesso FFmpeg, produzindo PCM raw.
- **Mixer**: Mescla múltiplos sources de áudio em um único stream using numpy. Aplica os fatores de volume/fade calculados pelas entidades sobre os buffers — não decide valores, apenas executa a mixagem.
- **CommandRouter**: Coleta as mensagens de um canal Discord e despacha para o `Command` correspondente.

---

## Frameworks Externos / Main

Camada mais externa: bibliotecas, frameworks e o ponto de entrada da aplicação (*composition root*), separado dos Adaptadores.

- **DiscordBot**: *Composition root*. Instancia as implementações concretas (`YoutubeResolver`, `DiscordPlayer`, `FFmpegSource`, `Mixer`) e as injeta nos Casos de Uso através das Portas definidas na camada de Application. É o único arquivo que conhece todas as implementações concretas.

---

## Regra de Dependência

```
Frameworks Externos → Adapters → Application (Casos de Uso) → Domain (Entidades)
       ↑                  ↑               ↑                        ↑
  depende de         depende de      depende de              zero dependências
```

- **Domain**: zero dependências externas. Apenas dados e regras de negócio genéricas.
- **Application**: depende apenas de Domain. Define as Portas que precisa.
- **Adapters**: depende de Application (implementa as Portas) e de Domain.
- **Frameworks Externos**: depende de todos os anteriores. Instancia e conecta tudo.

---

## Estrutura de arquivos

```
src/harpi/
├── domain/                          # Entidades — zero dependências
│   ├── __init__.py
│   ├── track_metadata.py            # TrackMetadata
│   ├── background_track_id.py       # Value object (wrapper sobre UUID)
│   ├── loop_mode.py                 # LoopMode (TRACK, QUEUE, OFF)
│   └── volume.py                    # validate_volume(), MIN_VOLUME, MAX_VOLUME
├── application/                     # Casos de Uso — define Portas
│   ├── __init__.py
│   ├── player_service.py            # Orquestrador central
│   ├── track_factory.py             # Chama AudioResolverProtocol → TrackMetadata
│   ├── exceptions.py                # Exceções de domínio da aplicação
│   └── commands/                    # Um arquivo por comando
│       ├── __init__.py              # Registry de comandos (@register)
│       ├── play.py
│       ├── skip.py
│       ├── pause.py
│       ├── resume.py
│       ├── stop.py
│       ├── volume.py
│       ├── loop.py
│       ├── rm.py
│       ├── background_add.py
│       ├── background_remove.py
│       └── background_set.py
├── infrastructure/                  # Adaptadores — implementa Portas
│   ├── __init__.py
│   ├── youtube_resolver.py          # Implementa AudioResolverProtocol
│   ├── composite_source_resolver.py # Implementa AudioResolverProtocol (agrega)
│   ├── ffmpeg_source.py             # Source de áudio via FFmpeg
│   ├── mixer.py                     # Mixagem via numpy
│   ├── discord_player.py            # Implementa AudioPlayerProtocol
│   ├── command_router.py            # Traduz mensagens → Commands
│   └── discord_bot.py               # Composition root
└── main.py                          # Entry point
```
