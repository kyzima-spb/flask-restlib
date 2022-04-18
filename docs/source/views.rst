.. _views:


Классы представления
====================

lookup_names
------------

Если в классе представления определен атрибут ``lookup_names``,
то включается механизм сопоставления имен URL-параметров с именами атрибутов первичных ключей модели.

Он необходим, когда заранее не известны имена URL-параметров, либо имена атрибутов модели,
используемые для уникальной идентификации ресурса.

Если первичный ключ не составной, то в ``lookup_names`` требуется указать только одно имя,
которое не обязательно должно совпадать с именем атрибута первичного ключа модели.
Значение URL-параметра с указанным именем,
будет передано в именованный аргумент ``id`` методу представления.

Если первичный ключ составной,
то в ``lookup_names`` требуется перечислить имена атрибутов первичного ключа модели.
Важно, чтобы порядок перечисления совпадал с порядком, используемым при выборке в вашем ORM.
В метод представления будет передан именованный аргумент ``id``, имеющий тип словарь,
где ключ словаря это имя атрибута модели, а значение - значение из URL-параметра.

.. code-block:: python

    from flask_restlib.views import ApiView


    class UserView(ApiView):
        """
        Route: /users/<int:user_id>
        URL:   /users/1
        """
        lookup_names = ('user_id',)

        def get(id):
            # id == 1


    class GroupView(ApiView):
        """
        Route: /groups/<int:group_id>/members/<int:student_id>
        URL:   /groups/1/members/3
        """
        lookup_names = ('group_id', 'student_id')

        def put(id):
            # id == {group_id: 1, student_id: 3}

Не используйте ``lookup_names``, если имена URL-параметров, либо атрибутов модели известны заранее.
В этом случае вам подойдет стандартный механизм Flask:

.. code-block:: python

    from flask_restlib.views import ApiView

    class GroupView(ApiView):
        """
        Route: /groups/<int:group_id>/members/<int:student_id>
        URL:   /groups/1/members/3
        """

        def put(group_id, student_id):
            # group_id == 1, student_id == 3

Если ``lookup_names`` - пустой кортеж, то механизм сопоставления имен отключен.
