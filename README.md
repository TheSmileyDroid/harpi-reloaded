# Harpi Reloaded

Bot de Discord para mesas de TTRPG: toca música do YouTube, mescla sons de fundo com
ducking automático (o fundo abaixa quando a música principal toca) e gerencia a fila
com modos de loop. Construído com Arquitetura Limpa e TDD.

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
| `-bg <links>` / `-bgadd <link>` / `-bgrm <índice>` | Sons de fundo mixados |
| `-volume <0..1>` / `-bgvolume <0..1>` / `-duck <0..1>` | Volumes e ducking |

## Testes

Pirâmide com três níveis (as regras completas estão no [AGENTS.md](AGENTS.md)):

```bash
uv run pytest test/unit -v          # 280 testes: domain + application com fakes (~1s)
uv run pytest test/integration -v   # 13 testes: IO real (YouTube, FFmpeg, voz do Discord)
uv run pytest test/e2e -v           # 1 teste: jornada completa de usuário
uv run pytest test/                 # tudo + relatório de cobertura (88%)
```

Os testes de integração e e2e exigem `DISCORD_TOKEN`, `TEST_GUILD_ID` e
`TEST_VOICE_CHANNEL_ID` no ambiente. Sem essas variáveis, são pulados automaticamente.

O mutmut verifica a qualidade da própria suíte:

```bash
uv run mutmut run    # 201/201 mutantes mortos
```

Suíte completa de verificação (type check + lint + dead code + testes):

```bash
uv run ty check src/harpi/ test/ main.py && uv run ruff check src/ test/ && uv run vulture && uv run pytest test/ -v
```

## Arquitetura

Arquitetura Limpa em três camadas mais o composition root. Os detalhes estão em
[docs/architecture.md](docs/architecture.md):

```
domain/          entidades puras (Queue, Background, LoopMode, volume), sem dependências
application/     casos de uso (PlayerService, comandos) + Portas (Protocol)
infrastructure/  adaptadores (YoutubeResolver, DiscordPlayer, mixagem numpy/FFmpeg)
```

Material da apresentação do projeto: [docs/apresentacao.md](docs/apresentacao.md).

## Funcionalidades planejadas

- Suporte a Spotify e streams ao vivo do YouTube
- TTS (text-to-speech) mixado com a música
- Interface web para gerenciar a fila
- Ferramentas de mesa (dados, iniciativa) para TTRPG
