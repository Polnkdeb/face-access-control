# Face Access Control

PoC системы прохода сотрудников по распознаванию лица.

Идея решения: кадр обрабатывается на edge-узле проходной. Система проверяет качество изображения и liveness, получает embedding лица, ищет совпадение в базе сотрудников и возвращает `allow`, `deny` или `manual_review`.

## Запуск

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python poc/demo.py
```

Smoke-test:

```bash
pytest -q
```

## Сценарии

В demo есть два события.

### Happy path — `e-1001`

Лицо найдено, quality и liveness проходят пороги, embedding уверенно совпадает с разрешённым сотрудником.

Результат:

```text
decision = allow
turnstile_command = open
```

### Risky path — `e-1003`
liveness score ниже порога - сомнительный случай, тогда турникет не открывается автоматически. 

Результат:

```text
decision = manual_review
turnstile_command = null
requires_human_review = true
```

Все решения пишутся в:

```text
poc/audit.jsonl
```

## Что реализовано

В PoC есть:

- проверки quality и liveness;
- сравнение embeddings через cosine similarity;
- выбор лучшего кандидата и расчёт margin до второго;
- логика `allow / deny / manual_review`;
- mock-команда открытия турникета;
- audit log;
- smoke-test.

Используются только искусственные demo-эмбеддинги, реальных биометрических данных в проекте нет.

В целевой системе pipeline выглядит так:

```text
face detection
→ quality
→ alignment
→ liveness
→ embedding
→ ANN search
→ decision
```

Для небольшой demo-базы используется прямое сравнение embeddings. При масштабировании до сотен тысяч лиц нужен ANN-индекс.

Пороги в PoC демонстрационные. Для реальной системы их нужно выбирать на validation set с учётом FAR и FRR.

## Ограничения

В PoC нет реальной камеры, CV-моделей, ANN-индекса, центрального сервиса и настоящей интеграции с турникетом. Также не реализован полноценный offline-режим. Эти части описаны в `docs/`.

Для бизнеса система должна уменьшить зависимость от физических карт и ускорить типовые проходы сотрудников. Это также снижает количество случаев, которые охране приходится разбирать вручную. При этом сомнительные события остаются на ручной проверке и не приводят к автоматическому открытию турникета.