# Story de mercado

Gera e publica o Story diário de mercado do @impostodabolsa: Brent (US$/barril), minério de ferro em Dalian (yuans/t, contrato contínuo `nf_I0` da Sina) e dólar.

## Como roda

- `python3 story.py gerar` monta `saida/story.jpg` (1080x1920) com Chrome headless.
- `python3 story.py publicar <url>` publica a imagem como Story pela Graph API.
- `python3 story.py pregao` sai com 0 se hoje tem pregão na B3.
- `python3 teste_story.py` roda os testes.

O workflow `.github/workflows/story.yml` roda seg-sex às 10:30 UTC (7h30 em Brasília). O GitHub costuma atrasar crons em alguns minutos. O job agendado:

1. pula sem erro enquanto o secret `IG_ACCESS_TOKEN` não existir;
2. pula sem erro em feriado da B3 (lista `FERIADOS_B3` em `story.py`, conferir no fim de cada ano);
3. gera a imagem, faz commit dela (a Meta exige URL pública) e publica.

Rodar à mão sem publicar: `gh workflow run story.yml -R profadriano240/story-mercado -f publicar=false`.

## Credenciais

- Variável `IG_USER_ID` (conta @impostodabolsa) já gravada no repo.
- Secret `IG_ACCESS_TOKEN`: token sem expiração do usuário do sistema `story-bot`, com `instagram_basic`, `instagram_content_publish`, `pages_show_list` e `business_management`. Só o Adriano gera e grava: `gh secret set IG_ACCESS_TOKEN -R profadriano240/story-mercado`.

## Aviso de falha no WhatsApp (não implementado)

As credenciais do CallMeBot (`CALLMEBOT_PHONE`, `CALLMEBOT_APIKEY`) ficam só no repo privado `cotacoes-b3`. Duas formas de ligar:

- **Sem secret novo:** um workflow agendado em `cotacoes-b3` (ex.: 11:15 UTC seg-sex) lê a API pública `https://api.github.com/repos/profadriano240/story-mercado/actions/runs?event=schedule&per_page=1` e, se a conclusão for `failure`, manda mensagem pelo CallMeBot.
- **Com secret novo:** gravar `CALLMEBOT_PHONE` e `CALLMEBOT_APIKEY` também neste repo e adicionar um passo `if: failure()` que chama `https://api.callmebot.com/whatsapp.php`.

Enquanto isso, o GitHub manda e-mail de falha do workflow para o dono do repo.
