# Roteiro de apresentação (20 a 25 min)

Harpi Reloaded é um bot de Discord para mesas de RPG. Toca música, mistura sons de
fundo com ducking automático (o fundo abaixa quando a música principal entra) e
controla a fila com modos de loop.

A ideia da apresentação: o sistema toma decisões de verdade, e cada técnica vista na
disciplina aparece aplicada em algum ponto da suíte. O número para deixar na cabeça
do professor: 201 de 201 mutantes mortos.

---

## 1. Abertura: o problema e as regras de negócio (2 min)

Não é CRUD. Decisões que o sistema toma:

| Regra | Onde vive |
|---|---|
| Próxima música conforme `LoopMode` (OFF / TRACK / QUEUE) | `domain/queue.py` |
| Rotação infinita de sons de fundo, identidade por `BackgroundTrackId` | `domain/background.py` |
| Validação de volume 0.0 a 1.0 (volume, bgvolume, duck) | `domain/volume.py` |
| Ducking: abaixar o fundo quando o principal toca, restaurar depois | `PlayerService` + `DiscordPlayer` |
| Substituição de fundos com falha parcial (N resolvem, M falham) | `PlayerService.set_background_tracks` |
| Tradução de erros externos em exceções da aplicação (link inválido, timeout, rede) | `YoutubeResolver` |

## 2. Demo ao vivo (4 a 5 min)

Antes de começar: bot rodando (`uv run python main.py`), já conectado no servidor,
canal de voz aberto e com áudio compartilhado.

Sequência no Discord (prefixo `-`):

1. `-play <link>`, a música começa
2. `-queue` mostra a fila e o modo de loop
3. `-loop queue`
4. `-bgadd <link>`, o som de fundo entra mixado por cima da música
5. `-duck 0.1`, dá para ouvir o fundo abaixar
6. `-volume 0.5`, `-skip`, `-stop`
7. `-help` no final (é gerado a partir do registry de comandos)

Plano B se a rede falhar: rodar `uv run pytest test/ -v` e mostrar o e2e
`test_user_plays_track_and_stops`, que sobe o bot num canal de voz de verdade.

## 3. Arquitetura a serviço da testabilidade (3 min)

Abrir `docs/architecture.md` no diagrama de dependência. Pontos que valem fala:

- O domain não importa nada de fora. Por isso os testes de unidade rodam em ~1s e dá
  para rodar mutação em massa sem sofrer.
- A application só conhece as portas (`Protocol` em `application/ports/audio.py`).
  Trocar o Discord por um fake é passar outro objeto no construtor.
- discord.py, pytubefix, FFmpeg e numpy ficam presos na infrastructure.
- `HarpiBot` é o composition root, o único arquivo que conhece as classes concretas.

## 4. Os testes, técnica por técnica (10 a 11 min)

### 4.1 Teste funcional: classes de equivalência (Aula 2)

`test/unit/domain/test_track_metadata.py::test_source_id` é parametrizado com as
classes válidas (YouTube longo, youtu.be, Spotify). Em
`test_player_service.py::TestPlayerServiceWithFailingResolver`, cada classe inválida
(link vazio, não YouTube, vídeo privado, timeout, erro de rede) tem teste separado.
Nunca duas classes inválidas no mesmo teste, regra registrada no AGENTS.md.

### 4.2 Análise de valor limite (Aula 4)

`test_track_metadata.py::TestValidateVolumeBVA` cobre todos os pontos: mínimo (0.0),
logo acima (0.001), meio, logo abaixo do máximo (0.999), máximo (1.0), abaixo (-0.1)
e acima (1.1). Vale o mesmo para os índices de `-rm` e `-bgrm`: fora dos limites
levanta `IndexError`.

### 4.3 Dublês de teste (Aula 13)

`test/unit/conftest.py` define `FakeResolver` e `FakePlayer`, escritos à mão. O
projeto não usa `unittest.mock` nem `MagicMock` em lugar nenhum. É o estilo Detroit:
o teste verifica o estado que sobrou, não quais métodos foram chamados.
`FakeResolver.set_failure(link, exc)` simula erro de rede de forma determinística.

### 4.4 Pirâmide de testes (Aula 10)

- 280 testes de unidade (domain e application com fakes, ~1s)
- 13 de integração (IO real: YouTube, FFmpeg e canal de voz do Discord; sem
  credenciais no ambiente, são pulados)
- 1 e2e (mensagem no chat vira comando, comando vira áudio no canal)
- O CI roda os três estágios em jobs separados (mostrar o `ci.yml` se der tempo)

### 4.5 Cobertura estrutural (Aulas 6 e 7)

`uv run pytest test/` imprime o relatório do pytest-cov: 88% no total. Domain e
application ficam perto de 100%. O que falta é quase todo código de borda com o
Discord real.

### 4.6 Teste de mutação (Aula 9)

```bash
uv run mutmut run   # 201/201 mutantes mortos
```

Como foi na prática, em quatro passos:

1. Primeira rodada: 205 mutantes, 5 sobreviventes.
2. Os diffs (`mutmut show`) mostraram 2 lacunas reais. Ninguém testava a mensagem do
   `KeyError` de `Background.remove_entry`, e a troca de sons de fundo passava com
   `range(..., -2)` porque o teste usava só 1 track pré-existente.
3. Dois testes novos mataram esses mutantes (commit `test: kill surviving mutants...`).
4. Os 3 restantes eram equivalentes por artefato da ferramenta: o trampoline do mutmut
   captura os defaults na assinatura original, então mutar um default nunca muda o
   comportamento. Ficaram na whitelist com `# pragma: no mutate` e um comentário.

### 4.7 TDD (estilo Detroit)

O fluxo RED, GREEN, REFACTOR está no AGENTS.md e dá para ver no histórico: os fakes e
os testes do `DiscordPlayer` entraram antes do player real (SMI-7).

## 5. Caso real: a suíte pegou uma regressão externa (2 min)

O playback quebrou sem nenhuma mudança no nosso código. O YouTube passou a servir URLs
SABR para o client WEB e o FFmpeg parou de abrir o stream. O teste
`test_play_real_audio_stream` acusou, o diagnóstico isolou a camada (a resolução de
metadados funcionava, o streaming não) e a correção foi trocar para o client
`ANDROID_VR` (commit `fix: use ANDROID_VR client...`). Teste de integração com IO real
serve para isso: dependência externa muda sem avisar.

## 6. Fechamento (1 min)

Recapitular os números: 294 testes em três níveis, 88% de cobertura, 201/201 na
mutação, CI verde. Se sobrar tempo, mostrar o `ci.yml` com os três estágios.

---

## Divisão sugerida entre os membros

| Bloco | Conteúdo | Tempo |
|---|---|---|
| 1 e 2 | Contexto, regras de negócio e demo | ~7 min |
| 3 | Arquitetura e portas | ~3 min |
| 4.1 a 4.3 | Funcional, BVA e dublês | ~5 min |
| 4.4 a 4.7 | Pirâmide, cobertura, mutação, TDD | ~6 min |
| 5 e 6 | Caso real e fechamento | ~3 min |

## Perguntas prováveis do professor

- "Por que não usam mock?" Seguimos o estilo Detroit: fake com estado deixa o teste
  verificar o resultado em vez da interação, e quebra menos quando o código interno
  muda. O contrato fica no `Protocol` da porta.
- "O que é um mutante equivalente?" Mutação sem efeito observável. Temos um caso
  concreto para mostrar, o do trampoline (seção 4.6).
- "Por que a cobertura não é 100%?" O que falta é integração com o Discord. Cobrir
  isso em unidade exigiria mockar o framework; a gente verifica por integração e e2e.
- "Como o teste de unidade não toca a rede?" Portas e injeção de dependência. Mostrar
  o construtor de `PlayerService`.
