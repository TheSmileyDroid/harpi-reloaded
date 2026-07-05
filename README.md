# Harpi Reloaded

[![codecov](https://codecov.io/github/TheSmileyDroid/harpi-reloaded/graph/badge.svg?token=MYJ7OHWY5B)](https://codecov.io/github/TheSmileyDroid/harpi-reloaded)

Bot de Discord para mesas de TTRPG. Toca música do YouTube, mescla sons de fundo com
ducking automático (o fundo abaixa quando a música principal toca) e gerencia a fila
com modos de loop.

Remake do [Harpi](https://github.com/TheSmileyDroid/harpi) original, reescrito do zero
com foco em estabilidade e teste automatizado.

## Quickstart

Requisitos: Python 3.12+, [uv](https://docs.astral.sh/uv/), FFmpeg no PATH.

```bash
uv sync                      # instala dependências
cp .env.example .env         # configure DISCORD_TOKEN (e opcional BOT_PREFIX)
uv run python main.py        # inicia o bot
```

No Discord (prefixo padrão `-`):

| Comando | Efeito |
|---|---|
| `-play <link>` | Toca ou enfileira uma música do YouTube |
| `-queue` | Mostra a fila e o modo de loop |
| `-loop [off\|track\|queue]` | Alterna o modo de loop |
| `-skip` / `-pause` / `-resume` / `-stop` | Controle de reprodução |
| `-rm <índice>` | Remove música da fila |
| `-bg <links>` / `-bgadd <link>` / `-bgrm <índice>` | Sons de fundo mixados, em loop até serem removidos |
| `-volume <0..1>` / `-bgvolume <0..1>` / `-duck <0..1>` | Volumes e ducking |
| `-help` | Lista os comandos com descrição |

## Testes

Três níveis de teste:

```bash
uv run pytest test/unit -v          # domain + application com fakes
uv run pytest test/integration -v   # IO real (YouTube, FFmpeg, voz do Discord)
uv run pytest test/e2e -v           # jornada completa de usuário
uv run pytest test/                 # tudo + relatório de cobertura
```

Os testes de integração e e2e exigem `DISCORD_TOKEN`, `TEST_GUILD_ID` e
`TEST_VOICE_CHANNEL_ID` no ambiente. Sem essas variáveis, são pulados automaticamente.

Verificação de qualidade dos testes com mutmut:

```bash
uv run mutmut run
```

Suíte completa de verificação:

```bash
uv run ty check src/harpi/ test/ main.py && uv run ruff check src/ test/ && uv run vulture && uv run pytest test/ -v
```

## Arquitetura

Arquitetura Limpa em três camadas mais o composition root. Detalhes em
[docs/architecture.md](docs/architecture.md):

```
domain/          entidades puras (Queue, LoopMode, volume), sem dependências
application/     casos de uso (PlayerService, comandos) + Portas (Protocol)
infrastructure/  adaptadores (YoutubeResolver, DiscordPlayer, mixagem numpy/FFmpeg)
```

## Funcionalidades planejadas

- Suporte a Spotify e streams ao vivo do YouTube
- TTS (text-to-speech) mixado com a música
- Interface web para gerenciar a fila
- Ferramentas de mesa (dados, iniciativa) para TTRPG
