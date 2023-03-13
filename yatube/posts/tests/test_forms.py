from http import HTTPStatus

from django.test import Client, TestCase
from django.urls import reverse

from yatube.settings import USER_NAME

from ..models import Group, Post, User


class PostFormTests(TestCase):
    def setUp(self):
        self.user = User.objects.create(username=USER_NAME)
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)

    def test_create_post(self):
        """Валидная форма создает запись в Post."""
        posts_count = Post.objects.count()
        form_data = {"text": "Введите текст"}
        response = self.authorized_client.post(
            reverse("posts:post_create"), data=form_data, follow=True
        )
        self.assertRedirects(
            response, reverse(
                "posts:profile",
                kwargs={"username": self.user.username})
        )
        self.assertEqual(Post.objects.count(), posts_count + 1)
        self.assertTrue(Post.objects.filter(text=form_data["text"]).exists())
        self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_post_edit(self):
        """Валидная форма изменяет запись в Post."""
        self.post = Post.objects.create(
            author=self.user,
            text="Текст поста.",
        )
        self.group = Group.objects.create(
            title="Тестовая группа.",
            slug="test-slug",
            description="Описание.",
        )
        posts_count = Post.objects.count()
        form_data = {"text": "Измененный текст.", "group": self.group.id}
        response = self.authorized_client.post(
            reverse("posts:post_edit", args=({self.post.id})),
            data=form_data,
            follow=True,
        )
        self.assertRedirects(
            response, reverse(
                "posts:post_detail",
                kwargs={"post_id": self.post.id})
        )
        edited_post = Post.objects.get(id=self.post.id)
        self.assertEqual(Post.objects.count(), posts_count)
        self.assertEqual(Post.objects.latest('id').author, self.user)
        self.assertEqual(
            edited_post.text, form_data["text"]
        )
        self.assertEqual(
            edited_post.group.id, form_data["group"]
        )
        self.assertEqual(response.status_code, HTTPStatus.OK)
