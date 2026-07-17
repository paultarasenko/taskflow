"""Connection manager для WebSocket-соединений.

Отклонение от стандартного шаблона модуля (см. docs/01-architecture-and-design.md,
раздел 3): у `websocket` нет `model.py` — модуль не владеет персистентными данными,
только держит активные соединения в памяти процесса и делает fan-out через Redis
Pub/Sub между инстансами API. Поэтому `repository.py` заменён на `connection_manager.py`
— по смыслу это тот же "доступ к ресурсу", только ресурс не в Postgres, а in-memory.

TODO(Этап 8): реализация вместе с realtime-функциями.
"""


class ConnectionManager:
    """Хранит активные WS-соединения по `project_id`, публикует/принимает
    события через Redis Pub/Sub канал `project:{id}` (см. раздел 5.10 API-дизайна).
    """

    ...
