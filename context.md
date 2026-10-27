Percebi o conceito. O Proxy as Code não deve ser apenas mais um proxy HTTP em Python: deve funcionar como uma camada de captura, transformação, organização e reprodução de tráfego HTTP, preparada para alimentar uma IA especializada em pentest.

A ideia central é transformar cada interação HTTP numa unidade de código reproduzível, mantendo a fidelidade da comunicação original. Assim, a IA não precisa de interpretar manualmente milhares de linhas de tráfego: consegue pesquisar, comparar, analisar e voltar a executar pedidos de forma controlada.

## 1. Arquitectura proposta

Cliente / Aplicação alvo

Browser, Android, API ou ferramenta de teste

## Proxy Core

Captura bidireccional de requests e responses

Domain Filter

Incluir, excluir e agrupar domínios.

Policy Engine

Scope autorizado, limites e controlo de execução.

Request Compiler

Converte tráfego em código reutilizável.

Traffic Store

Histórico, metadados, corpos e respostas originais.

AI Pentest Interface

Pesquisa de tráfego, análise de diferenças, obtenção de requests e replay controlado.

A regra mais importante da arquitectura é separar três coisas: o tráfego original, a representação em código e a execução da request. Não devem ser a mesma entidade nem partilhar responsabilidades desnecessariamente.

## 2. Estrutura do projecto Python

Eu organizaria o repositório por responsabilidades, evitando um único ficheiro com captura, filtros, persistência, geração de código e execução.

```
proxy-as-code/
├── pyproject.toml
├── README.md
├── .env.example
├── src/
│   └── proxy_as_code/
│       ├── __init__.py
│       ├── main.py
│       ├── config.py
│       │
│       ├── proxy/
│       │   ├── server.py
│       │   ├── lifecycle.py
│       │   └── addons.py
│       │
│       ├── capture/
│       │   ├── handler.py
│       │   ├── normalizer.py
│       │   └── models.py
│       │
│       ├── filtering/
│       │   ├── domains.py
│       │   └── rules.py
│       │
│       ├── storage/
│       │   ├── repository.py
│       │   ├── database.py
│       │   └── blobs.py
│       │
│       ├── compiler/
│       │   ├── python.py
│       │   ├── curl.py
│       │   └── manifest.py
│       │
│       ├── replay/
│       │   ├── executor.py
│       │   ├── safety.py
│       │   └── comparison.py
│       │
│       ├── api/
│       │   ├── routes.py
│       │   └── schemas.py
│       │
│       └── ai/
│           ├── tools.py
│           └── context.py
│
├── tests/
│   ├── unit/
│   ├── integration/
│   ├── fixtures/
│   └── security/
│
└── docs/
    ├── architecture.md
    ├── api.md
    └── threat-model.md
```

### Responsabilidade de cada módulo

| Módulo       | Responsabilidade                                     |
| ------------ | ---------------------------------------------------- |
| `proxy/`     | Receber e encaminhar o tráfego HTTP/HTTPS.           |
| `capture/`   | Construir o registo fiel da request e response.      |
| `filtering/` | Aplicar regras de domínio, portas e exclusões.       |
| `storage/`   | Persistir tráfego, corpos binários e metadados.      |
| `compiler/`  | Gerar representações executáveis e exportáveis.      |
| `replay/`    | Executar requests guardadas e comparar resultados.   |
| `api/`       | Expor operações para CLI, interface e agentes de IA. |
| `ai/`        | Fornecer ferramentas e contexto estruturado à IA.    |

Uma decisão importante: não criaria uma classe genérica para cada ficheiro apenas para aumentar o número de abstrações. Cada módulo deve existir porque tem uma responsabilidade real, e cada função deve ter um propósito claro.

## 3. Como preservar requests e responses

Este é o núcleo do projecto. Cada transacção deve possuir um identificador estável e conservar os dados originais.

Original Record

Método, URL, headers, corpo em bytes, protocolo, timestamps, estado da resposta, headers de resposta e corpo da resposta.

Generated Artifact

Código Python, cURL, metadados de execução e referência ao registo original.

Replay Result

Request efectivamente enviada, resposta recebida, diferenças e ligação à transacção original.

Por exemplo, uma request capturada:

```
POST /api/v1/profile HTTP/1.1
Host: api.example.test
Authorization: Bearer <TOKEN>
Content-Type: application/json

{"name":"Test User"}
```

Poderia gerar este artefacto Python:

```
import httpxdef replay_profile(base_url: str, token: str) -> httpx.Response:    request = {        "method": "POST",        "url": f"{base_url}/api/v1/profile",        "headers": {            "Authorization": f"Bearer {token}",            "Content-Type": "application/json",        },        "content": b'{"name":"Test User"}',    }    with httpx.Client(timeout=15.0) as client:        return client.request(**request)
```

O exemplo é ilustrativo. Num artefacto real, o compilador deve tratar correctamente query strings, cookies, corpos binários, parâmetros repetidos, codificação, headers específicos e outros detalhes da request capturada.

### Uma limitação que não deves ignorar

Preservar uma request em código não significa que ela possa ser reproduzida byte a byte. Uma biblioteca HTTP pode alterar headers, normalizar URLs, negociar HTTP/2 ou reconstruir o enquadramento da mensagem.

Por isso, o sistema deve distinguir:

- Fidelidade de captura: guardar os bytes e metadados disponíveis no ponto de interceptação.
- Replay semântico: reproduzir o método, URL, headers e corpo com o mesmo significado.
- Replay de baixo nível: preservar, na medida tecnicamente possível, detalhes de serialização e protocolo.

Para HTTPS, a captura do conteúdo exige normalmente interceptação TLS com uma CA de teste confiada pelo cliente. O tráfego com certificate pinning, mTLS ou mecanismos específicos pode exigir configuração adicional. Não prometas suporte universal sem o testar.

## 4. Filtragem por domínio

A filtragem deve funcionar como política central, não como vários `if` espalhados pelo código.

Exemplo de configuração:

```
proxy:
  host: "127.0.0.1"
  port: 8080

capture:
  include_domains:
    - "example.test"
    - "*.api.example.test"

  exclude_domains:
    - "analytics.example.test"

  store_bodies: true

replay:
  require_approval: true
  allowed_domains:
    - "example.test"
```

O comportamento esperado:

- Os domínios incluídos são capturados.
- As exclusões prevalecem sobre as inclusões.
- `example.test` não deve corresponder automaticamente a `notexample.test`.
- `*.api.example.test` deve ter uma semântica de correspondência documentada.
- O tráfego não incluído deve ser encaminhado normalmente, se essa for a política configurada, sem ser persistido.
- O domínio autorizado para captura não deve ser automaticamente considerado autorizado para replay.

Também separaria a filtragem de captura da política de execução. São decisões de segurança diferentes.

## 5. Interface para uma IA de pentest

A IA não deve precisar de ler ficheiros de milhares de linhas nem de receber todo o histórico em cada chamada. Deve conseguir consultar o proxy através de operações pequenas e estruturadas.

| Operação            | Finalidade                                                           |
| ------------------- | -------------------------------------------------------------------- |
| `search_requests`   | Pesquisar por domínio, método, caminho, estado e intervalo temporal. |
| `get_transaction`   | Obter a request e response completas.                                |
| `get_artifact`      | Obter o código gerado para uma transacção.                           |
| `replay_request`    | Reexecutar uma request autorizada.                                   |
| `compare_responses` | Comparar resposta original e resposta do replay.                     |
| `export_session`    | Exportar uma sessão de teste organizada.                             |

A IA poderia, por exemplo, pedir todas as requests para `/api/v1/accounts`, seleccionar uma request de consulta e outra de alteração, comparar as respostas e propor testes adicionais de autorização.

O resultado deve incluir referências às transacções que sustentam a análise. A IA deve conseguir distinguir factos observados, hipóteses e conclusões confirmadas.

Não confundas capacidade de execução com inteligência de análise. O proxy fornece evidências e ferramentas; a IA interpreta os resultados e propõe experiências.

