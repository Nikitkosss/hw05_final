from django import forms
from django.core.cache import cache
from django.test import Client, TestCase
from django.urls import reverse

from yatube.settings import FIRST_TEN_VALUE

from ..models import Comment, Group, Post, User, Follow


class PostPagesTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create(username="Nikita")
        cls.group = Group.objects.create(
            title="Тестовая группа",
            slug="test-slug",
            description="Тестовое описание",
        )
        cls.post = Post.objects.create(
            author=cls.user,
            text="Тестовая пост",
            group=cls.group,
        )
        cls.templates_pages_names = {
            reverse("posts:index"): "posts/index.html",
            reverse(
                "posts:group_list", kwargs={"slug": cls.group.slug}
            ): "posts/group_list.html",
            reverse(
                "posts:profile", kwargs={"username": cls.post.author}
            ): "posts/profile.html",
            reverse(
                "posts:post_detail", kwargs={"post_id": cls.post.id}
            ): "posts/post_detail.html",
            reverse(
                "posts:post_edit", kwargs={"post_id": cls.post.id}
            ): "posts/create_post.html",
            reverse("posts:post_create"): "posts/create_post.html",
        }

    def setUp(self):
        self.authorized_client = Client()
        self.authorized_client.force_login(PostPagesTests.user)
        cache.clear()

    def test_pages_uses_correct_template(self):
        """Сайт использует правильный шаблон"""
        for template, reverse_name in self.templates_pages_names.items():
            with self.subTest(reverse_name=reverse_name):
                response = self.authorized_client.get(template)
                self.assertTemplateUsed(response, reverse_name)

    def test_index_show_correct_context(self):
        """Список постов в шаблоне index равен 10."""
        response = self.client.get(reverse("posts:index"))
        expected = list(Post.objects.all()[:FIRST_TEN_VALUE])
        self.assertEqual(list(response.context["page_obj"]), expected)

    def test_group_list_show_correct_context(self):
        """Список постов в шаблоне group_list равен 10."""
        response = self.client.get(
            reverse("posts:group_list", kwargs={"slug": self.group.slug})
        )
        expected = list(
            Post.objects.filter(group_id=self.group.id)[:FIRST_TEN_VALUE],
        )
        self.assertEqual(list(response.context["page_obj"]), expected)

    def test_profile_show_correct_context(self):
        """Список постов в шаблоне profile равен 10."""
        response = self.client.get(
            reverse("posts:profile", args=(self.post.author,))
        )
        expected = list(
            Post.objects.filter(author_id=self.user.id)[:FIRST_TEN_VALUE],
        )
        self.assertEqual(list(response.context["page_obj"]), expected)

    def test_post_detail_show_correct_context(self):
        """Шаблон post_detail сформирован с правильно."""
        response = self.client.get(
            reverse("posts:post_detail", kwargs={"post_id": self.post.id})
        )
        self.assertEqual(response.context.get("post").text, self.post.text)
        self.assertEqual(response.context.get("post").id, self.post.pk)
        self.assertEqual(response.context.get("post").author, self.post.author)
        self.assertEqual(response.context.get("post").group, self.post.group)

    def test_create_edit_show_correct_context(self):
        """Шаблон create_edit сформирован с правильно."""
        response = self.authorized_client.get(
            reverse("posts:post_edit", kwargs={"post_id": self.post.id})
        )
        form_fields = {
            "text": forms.fields.CharField,
            "group": forms.models.ModelChoiceField,
        }
        for value, expected in form_fields.items():
            with self.subTest(value=value):
                form_field = response.context["form"].fields[value]
                self.assertIsInstance(form_field, expected)

    def test_create_show_correct_context(self):
        """Шаблон create сформирован с правильно."""
        response = self.authorized_client.get(reverse("posts:post_create"))
        form_fields = {
            "text": forms.fields.CharField,
            "group": forms.models.ModelChoiceField,
            "image": forms.fields.ImageField,
        }
        for value, expected in form_fields.items():
            with self.subTest(value=value):
                form_field = response.context["form"].fields[value]
                self.assertIsInstance(form_field, expected)

    def test_check_group_in_pages(self):
        """Проверяем создание поста на странице выбранной группы."""
        form_fields = {
            reverse("posts:index"): Post.objects.get(group=self.post.group),
            reverse(
                "posts:group_list", kwargs={"slug": self.group.slug}
            ): Post.objects.get(group=self.post.group),
            reverse(
                "posts:profile", kwargs={"username": self.post.author}
            ): Post.objects.get(group=self.post.group),
        }
        for value, expected in form_fields.items():
            with self.subTest(value=value):
                response = self.authorized_client.get(value)
                form_field = response.context["page_obj"]
                self.assertIn(expected, form_field)

    def test_check_group_not_in_mistake_group_list_page(self):
        """Проверяем что этот пост не попал не в ту группу."""
        form_fields = {
            reverse(
                "posts:group_list", kwargs={"slug": self.group.slug}
            ): Post.objects.exclude(group=self.post.group),
        }
        for value, expected in form_fields.items():
            with self.subTest(value=value):
                response = self.authorized_client.get(value)
                form_field = response.context["page_obj"]
                self.assertNotIn(expected, form_field)

    def test_comment_correct_context(self):
        """Форма Комментария создает запись в Post."""
        comments_count = Comment.objects.count()
        form_data = {"text": "Тестовый коммент"}
        response = self.authorized_client.post(
            reverse("posts:add_comment", kwargs={"post_id": self.post.id}),
            data=form_data,
            follow=True,
        )
        self.assertRedirects(
            response, reverse(
                "posts:post_detail",
                kwargs={"post_id": self.post.id},
            )
        )
        self.assertEqual(Comment.objects.count(), comments_count + 1)

    def test_check_cache(self):
        """Проверка кеша."""
        response = self.client.get(reverse("posts:index"))
        first_response = response.content
        Post.objects.get(id=1).delete()
        response2 = self.client.get(reverse("posts:index"))
        second_response = response2.content
        self.assertEqual(first_response, second_response)

    def test_follow_page(self):
        # Проверяем, что страница подписок пуста
        response = self.authorized_client.get(reverse("posts:follow_index"))
        self.assertEqual(len(response.context["page_obj"]), 0)
        # Проверка подписки на автора поста
        Follow.objects.get_or_create(user=self.user, author=self.post.author)
        response_2 = self.authorized_client.get(reverse("posts:follow_index"))
        self.assertEqual(len(response_2.context["page_obj"]), 1)
        # проверка подписки у юзера-фоловера
        self.assertIn(self.post, response_2.context["page_obj"])

        # Проверка что пост не появился в избранных у юзера-обычного
        outsider = User.objects.create(username="NoName")
        self.authorized_client.force_login(outsider)
        response_2 = self.authorized_client.get(reverse("posts:follow_index"))
        self.assertNotIn(self.post, response_2.context["page_obj"])

        # Проверка отписки от автора поста
        Follow.objects.all().delete()
        response_3 = self.authorized_client.get(reverse("posts:follow_index"))
        self.assertEqual(len(response_3.context["page_obj"]), 0)
