# Проверка изменения Material You

Платформа: x86_64-linux, NixOS, 11 ноября 2026.

* `make debug` в Nix dev shell: успешно.
* `ruff check .`, `git diff --check`: успешно.
* `nix flake check` с nixpkgs текущей системы: все 7 проверок успешно.
* Пакет с `doCheck = true`: 833 теста, OK, 5 штатных пропусков.
  В пакете применяются существующие Nix sandbox patches/exclusions.
* Проверены 12 конфигураций density × scheme × reduced; конфиги преобразуются
  также в C Options. Проверены обе baseline-темы и темы, генерируемые myt.
* Проверка контраста отвергает контрольную пару #777777/#777777,
  выдаёт корректный JSON и ненулевой код завершения.
* На реальном X11/NVIDIA открыто окно собранного форка с двумя вкладками:
  применены light/dark через remote control, проверено конечное значение
  фона, reload reduced_motion=yes, затем reduced_motion=no без перезапуска.
  Снимки: [dark](verified-dark.png), [light](verified-light.png).
* Вычисление пользовательской конфигурации NixOS с новым модулем: успешно.

Ограничения локального окружения: полный `./test.py` вне Nix sandbox дал
сбои fish/ssh shell integration; та же интеграция проходит в сборке Nix.
`./test.py type-check` с ty 0.0.98 показывает 7 предупреждений в прежнем
коде (deprecated contextmanager и unused type-ignore); ошибок типов
в изменённых файлах после исправлений нет. Предупреждения не скрывались
настройками проекта. Другие архитектуры и macOS здесь не запускались.
