# Roteiro de Apresentação — Projeto Final V&V (20–25 min)

**Projeto:** Harpi Reloaded — bot de Discord para mesas de TTRPG: toca música, mescla
sons de fundo com *ducking* automático e gerencia fila com modos de loop.

**Tese da apresentação:** um sistema com regras de negócio reais (mixagem, ducking,
looping, validações), verificado com as técnicas da disciplina — funcional, estrutural,
dublês, pirâmide e mutação — chegando a **100% de kill rate** no teste de mutação.

---

## 1. Abertura — o problema e as regras de negócio (2 min)

Não é CRUD. As decisões que o sistema toma:

| Regra | Onde vive |
|---|---|
| Próxima música conforme `LoopMode` (OFF / TRACK / QUEUE) | `domain/queue.py` |
| Rotação infinita de sons de fundo, identidade por `BackgroundTrackId` | `domain/background.py` |
| Validação de volume 0.0–1.0 (volume, bgvolume, duck) | `domain/volume.py` |
| Ducking: abaixar fundo quando o principal toca, restaurar depois | `PlayerService` + `DiscordPlayer` |
| Substituição transacional de fundos com falha parcial (N ok, M falham) | `PlayerService.set_background_tracks` |
| Tradução de erros externos → exceções da aplicação (link inválido, timeout, rede) | `YoutubeResolver` |

## 2. Demo ao vivo (4–5 min)

```bash
uv run python main.py
```

No Discord (prefixo `-`): `-play <link>` → `-queue` → `-loop queue` → `-bgadd <link>`
(fundo entra mixado) → `-duck 0.1` (fundo abaixa enquanto música toca) → `-volume 0.5`
→ `-skip` → `-stop`. Fechar com `-help` mostrando o registry de comandos.

> Plano B sem rede: rodar `uv run pytest test/ -v` e mostrar o e2e
> `test_user_plays_track_and_stops` que sobe o bot de verdade num canal de voz.

## 3. Arquitetura a serviço da testabilidade (3 min)

Mostrar `docs/architecture.md` e o diagrama de dependência:

- Domain sem NENHUM import externo → testável em milissegundos, mutável em massa.
- Application depende de **Portas** (`Protocol` em `application/ports/audio.py`) —
  injeção de dependência permite substituir Discord/YouTube por fakes.
- Infrastructure confina discord.py, pytubefix, FFmpeg e numpy.
- `HarpiBot` é o *composition root*: o único lugar que conhece as classes concretas.

## 4. Tour pelos testes — técnica por técnica (10–11 min)

### 4.1 Teste funcional: classes de equivalência (Aula 2)
`test/unit/domain/test_track_metadata.py::test_source_id` — parametrizado com classes
válidas (YouTube longo, youtu.be, Spotify) e `test_player_service.py::TestPlayerServiceWithFailingResolver`
— cada classe inválida (link vazio, não-YouTube, vídeo privado, timeout, rede) tem teste
separado, nunca duas classes inválidas no mesmo teste (regra do AGENTS.md).

### 4.2 Análise de Valor Limite (Aula 4)
`test_track_metadata.py::TestValidateVolumeBVA` — todos os pontos: mínimo (0.0), logo
acima (0.001), meio, logo abaixo do máximo (0.999), máximo (1.0), abaixo (-0.1) e acima
(1.1). Mesma disciplina nos índices de `-rm` e `-bgrm` (fora dos limites → `IndexError`).

### 4.3 Dublês de teste (Aula 13)
`test/unit/conftest.py`: `FakeResolver` e `FakePlayer` **escritos à mão**, implementando
as Portas — zero `unittest.mock`/`MagicMock` no projeto (estilo Detroit: verificação de
**estado**, não de interação). `FakeResolver.set_failure(link, exc)` simula erros de rede
deterministicamente.

### 4.4 Pirâmide de testes (Aula 10)
- **280 unit** (domain+application com fakes, ~1s)
- **13 integration** (IO real: YouTube, FFmpeg, canal de voz do Discord, marcados
  `@pytest.mark.integration`, com skip automático sem credenciais)
- **1 e2e** (jornada completa: mensagem → comando → áudio no canal)
- CI (GitHub Actions) roda os três estágios separados.

### 4.5 Cobertura estrutural (Aulas 6–7)
`uv run pytest test/ ` → **88% de cobertura total** (pytest-cov). Domain e Application
próximos de 100%; o que falta é majoritariamente código de borda com Discord real.

### 4.6 Teste de mutação (Aula 9) — o ponto alto
```bash
uv run mutmut run   # 201/201 mutantes mortos — 100% kill rate
```
Contar a história real:
1. Primeira rodada: 205 mutantes, **5 sobreviventes**.
2. Análise dos diffs (`mutmut show`): **2 gaps reais** — ninguém testava a mensagem do
   `KeyError` de `Background.remove_entry`, e a troca de fundos passava com
   `range(..., -2)` porque o teste usava só 1 track pré-existente.
3. Testes novos matam os 2 (ver commit `test: kill surviving mutants...`).
4. Os 3 restantes eram **mutantes equivalentes por artefato da ferramenta** (o trampoline
   do mutmut captura defaults na assinatura original — mutação no default nunca executa).
   Whitelisted com `# pragma: no mutate` + comentário, como manda a prática.

### 4.7 TDD (Detroit-style)
Fluxo RED → GREEN → REFACTOR documentado no AGENTS.md e visível no histórico de commits
(testes chegam junto ou antes das features; ex.: fakes e testes do `DiscordPlayer`
antes do player real — SMI-7).

## 5. Caso real: a suíte pegou uma regressão externa (2 min)

Os testes de integração acusaram que o playback quebrou **sem nenhuma mudança no nosso
código**: o YouTube passou a servir URLs SABR para o client WEB e o FFmpeg não abria o
stream. O teste `test_play_real_audio_stream` falhou, o diagnóstico isolou a camada
(resolução OK, streaming morto) e a correção foi trocar para o client `ANDROID_VR`
(commit `fix: use ANDROID_VR client...`). **É exatamente para isso que testes de
integração com IO real existem** — dependências externas mudam sob nossos pés.

## 6. Fechamento (1 min)

- 294 testes, 3 níveis, 88% cobertura, 100% mutation kill rate, CI verde.
- Qualidade vem da arquitetura (portas + fakes) tanto quanto dos testes.

---

## Divisão sugerida entre os membros

| Bloco | Conteúdo | Tempo |
|---|---|---|
| 1–2 | Contexto, regras de negócio e demo | ~7 min |
| 3 | Arquitetura e portas | ~3 min |
| 4.1–4.3 | Funcional, BVA e dublês | ~5 min |
| 4.4–4.7 | Pirâmide, cobertura, mutação, TDD | ~6 min |
| 5–6 | Caso real e fechamento | ~3 min |

## Perguntas prováveis do professor

- *"Por que não usam mock?"* → Detroit school: fakes com estado verificável são menos
  frágeis que asserção de interação; o contrato é o `Protocol` da porta.
- *"O que é um mutante equivalente?"* → mutação sem efeito observável; mostrar o caso
  do trampoline (seção 4.6).
- *"Por que a cobertura não é 100%?"* → o resto é código de integração com Discord;
  cobri-lo em unit test exigiria mockar o framework — verificamos por integração/e2e.
- *"Como o teste de unidade não toca a rede?"* → portas + injeção; mostrar o construtor
  de `PlayerService`.
