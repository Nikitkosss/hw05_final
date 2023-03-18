from django.contrib.auth import get_user_model
from django.test import TestCase

from yatube.settings import FIRST_FIFTEEN_VALUE, USER_NAME

from ..models import Group, Post

User = get_user_model()


class PostModelTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username=USER_NAME)
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='Тестовый слаг',
            description='Тестовое описание',
        )
        cls.post = Post.objects.create(
            author=cls.user,
            text='Тестовый пост',
        )

    def test_models_have_correct_object_names(self):
        values = (
            (str(self.post), self.post.text[:FIRST_FIFTEEN_VALUE]),
            (str(self.group), self.group.title),
        )
        for value, expected in values:
            with self.subTest(value=value):
                self.assertEqual(value, expected)
