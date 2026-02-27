# Installation

## Python (pip)

```bash
pip install texthumanize
```

### From Source

```bash
git clone https://github.com/ksanyok/TextHumanize.git
cd TextHumanize
pip install -e .
```

### Development Setup

```bash
git clone https://github.com/ksanyok/TextHumanize.git
cd TextHumanize
pip install -e ".[dev]"
pre-commit install
```

## Docker

```bash
docker build -t texthumanize .
docker run -p 8080:8080 texthumanize
```

The Docker image runs the REST API server on port 8080 by default.

```bash
# Process a file
docker run -v $(pwd):/data texthumanize /data/input.txt -o /data/output.txt
```

## PHP

```bash
cd php/
composer install
```

```php
use TextHumanize\TextHumanize;

$th = new TextHumanize();
$result = $th->humanize("Your text here.", "en");
```

## TypeScript / JavaScript

```bash
cd js/
npm install
```

```typescript
import { humanize } from './texthumanize';

const result = humanize("Your text here.", { lang: "en" });
```

## Requirements

| Platform | Minimum Version |
|----------|----------------|
| Python | 3.9+ |
| PHP | 8.1+ |
| Node.js | 18+ |

**Dependencies:** Zero. TextHumanize uses only the standard library.
