# Roteiro de apresentação (20 a 25 min)

Projeto: Harpi Reloaded, um bot de Discord para mesas de TTRPG. Toca música, mescla
sons de fundo com ducking automático (o fundo abaixa quando a música principal toca)
e gerencia a fila com modos de loop.

O argumento que amarra a apresentação: o sistema tem regras de negócio de verdade, e
cada técnica vista na disciplina aparece aplicada em algum ponto da suíte. Hoje a
suíte mata 201 de 201 mutantes.

---

## 1. Abertura: o problema e as regras de negócio (2 min)

Não é CRUD. Algumas decisões que o sistema toma:

| Regra | Onde vive |
|---|---|
| Próxima música conforme `LoopMode` (OFF / TRACK / QUEUE) | `domain/queue.py` |
| Rotação infinita de sons de fundo, identidade por `BackgroundTrackId` | `domain/background.py` |
| Validação de volume 0.0 a 1.0 (volume, bgvolume, duck) | `domain/volume.py` |
| Ducking: abaixar o fundo quando o principal toca, restaurar depois | `PlayerService` + `DiscordPlayer` |
| Substituição de fundos com falha parcial (N resolvem, M falham) | `PlayerService.set_background_tracks` |
| Tradução de erros externos em exceções da aplicação (link inválido, timeout, rede) | `YoutubeResolver` |

## 2. Demo ao vivo (4 a 5 min)

```bash
uv run python main.py
```

No Discord (prefixo `-`): `-play <link>`, depois `-queue`, `-loop queue`,
`-bgadd <link>` para o fundo entrar mixado, `-duck 0.1` para ouvir o fundo abaixar
enquanto a música toca, `-volume 0.5`, `-skip`, `-stop`. O `-help` é gerado a partir
do registry de comandos e serve de fecho.

Plano B sem rede: rodar `uv run pytest test/ -v` e mostrar o e2e
`test_user_plays_track_and_stops`, que sobe o bot num canal de voz de verdade.

## 3. Arquitetura a serviço da testabilidade (3 min)

Mostrar `docs/architecture.md` e o diagrama de dependência.

- O domain não importa nada de fora. Roda em milissegundos e aguenta mutação em massa.
- A application depende de portas (`Protocol` em `application/ports/audio.py`).
  A injeção de dependência permite trocar Discord e YouTube por fakes.
- A infrastructure confina discord.py, pytubefix, FFmpeg e numpy.
- `HarpiBot` é o composition root, o único lugar que conhece as classes concretas.

## 4. Tour pelos testes, técnica por técnica (10 a 11 min)

### 4.1 Teste funcional: classes de equivalência (Aula 2)

`test/unit/domain/test_track_metadata.py::test_source_id` é parametrizado com as
classes válidas (YouTube longo, youtu.be, Spotify). Em
`test_player_service.py::TestPlayerServiceWithFailingResolver`, cada classe inválida
(link vazio, não YouTube, vídeo privado, timeout, erro de rede) tem teste separado.
Nunca duas classes inválidas no mesmo teste, regra registrada no AGENTS.md.

### 4.2 Análise de valor limite (Aula 4)

`test_track_metadata.py::TestValidateVolumeBVA` cobre todos os pontos: mínimo (0.0),
logo acima (0.001), meio, logo abaixo do máximo (0.999), máximo (1.0), abaixo (-0.1)
e acima (1.1). A mesma disciplina vale para os índices de `-rm` e `-bgrm`: fora dos
limites levanta `IndexError`.

### 4.3 Dublês de teste (Aula 13)

`test/unit/conftest.py` define `FakeResolver` e `FakePlayer` escritos à mão,
implementando as portas. O projeto não usa `unittest.mock` nem `MagicMock` em lugar
nenhum. É o estilo Detroit: verificação de estado, não de interação.
`FakeResolver.set_failure(link, exc)` simula erros de rede de forma determinística.

### 4.4 Pirâmide de testes (Aula 10)

- 280 testes de unidade (domain e application com fakes, rodam em ~1s)
- 13 de integração (IO real: YouTube, FFmpeg e canal de voz do Discord, marcados com
  `@pytest.mark.integration`; sem credenciais no ambiente, são pulados)
- 1 e2e (mensagem no chat vira comando, comando vira áudio no canal)
- O CI (GitHub Actions) roda os três estágios em jobs separados.

### 4.5 Cobertura estrutural (Aulas 6 e 7)

`uv run pytest test/` imprime o relatório do pytest-cov: 88% no total. Domain e
application ficam perto de 100%. O que falta é quase todo código de borda com o
Discord real.

### 4.6 Teste de mutação (Aula 9)

```bash
uv run mutmut run   # 201/201 mutantes mortos
```

Vale contar como foi na prática:

1. Primeira rodada: 205 mutantes, 5 sobreviventes.
2. A análise dos diffs (`mutmut show`) mostrou 2 lacunas reais. Ninguém testava a
   mensagem do `KeyError` de `Background.remove_entry`, e a troca de sons de fundo
   passava com `range(..., -2)` porque o teste usava só 1 track pré-existente.
3. Dois testes novos mataram esses mutantes (commit `test: kill surviving mutants...`).
4. Os 3 restantes eram mutantes equivalentes por artefato da ferramenta: o trampoline
   do mutmut captura os defaults na assinatura original, então mutar um default nunca
   muda o comportamento. Ficaram na whitelist com `# pragma: no mutate` e um
   comentário explicando o motivo.

### 4.7 TDD (estilo Detroit)

O fluxo RED, GREEN, REFACTOR está documentado no AGENTS.md e aparece no histórico:
os fakes e os testes do `DiscordPlayer` entraram antes do player real (SMI-7).

## 5. Caso real: a suíte pegou uma regressão externa (2 min)

O playback quebrou sem nenhuma mudança no nosso código. O YouTube passou a servir URLs
SABR para o client WEB e o FFmpeg não abria mais o stream. O teste
`test_play_real_audio_stream` falhou, o diagnóstico isolou a camada (a resolução de
metadados funcionava, o streaming não) e a correção foi trocar para o client
`ANDROID_VR` (commit `fix: use ANDROID_VR client...`). Testes de integração com IO
real existem para pegar esse tipo de coisa: dependência externa muda sem avisar.

## 6. Fechamento (1 min)

294 testes em três níveis, 88% de cobertura, 201/201 no teste de mutação, CI verde.
A qualidade vem tanto da arquitetura (portas e fakes) quanto dos testes em si.

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

- "Por que não usam mock?" Estilo Detroit: fakes com estado verificável quebram menos
  que asserções de interação, e o contrato fica no `Protocol` da porta.
- "O que é um mutante equivalente?" Mutação sem efeito observável. Mostrar o caso do
  trampoline (seção 4.6).
- "Por que a cobertura não é 100%?" O que falta é integração com o Discord. Cobrir
  isso em teste de unidade exigiria mockar o framework; verificamos por integração e
  e2e.
- "Como o teste de unidade não toca a rede?" Portas e injeção de dependência. Mostrar
  o construtor de `PlayerService`.
