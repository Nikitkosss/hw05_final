import shutil
import tempfile
from http import HTTPStatus

from django.conf import settings
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from yatube.settings import USER_NAME

from ..models import Comment, Group, Post, User

TEMP_MEDIA_ROOT = tempfile.mkdtemp(dir=settings.BASE_DIR)


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class PostFormTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username="HasNoName")
        cls.group = Group.objects.create(
            title="Test group",
            slug="test_group_slug",
            description="Test group description",
        )
        cls.small_gif = (
            b"\x47\x49\x46\x38\x39\x61\x02\x00"
            b"\x01\x00\x80\x00\x00\x00\x00\x00"
            b"\xFF\xFF\xFF\x21\xF9\x04\x00\x00"
            b"\x00\x00\x00\x2C\x00\x00\x00\x00"
            b"\x02\x00\x01\x00\x00\x02\x02\x0C"
            b"\x0A\x00\x3B"
        )
        cls.uploaded = SimpleUploadedFile(
            name="small.gif", content=cls.small_gif, content_type="image/gif"
        )
        cls.post = Post.objects.create(
            author=cls.user,
            text="Тестовый текст",
            group=cls.group,
            image=cls.uploaded,
        )
        cls.form_data = {
            "text": "Тестовый коммент",
        }
        cls.url = reverse("posts:add_comment", args=[cls.post.id])

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

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)

    def test_image_in_group_list_page(self):
        """Картинка передается на страницу group_list."""
        response = self.client.get(
            reverse("posts:group_list", kwargs={"slug": self.group.slug}),
        )
        obj = response.context["page_obj"][0]
        self.assertEqual(obj.image, self.post.image)

    def test_image_in_index_and_profile_page(self):
        """Картинка передается на страницу index_and_profile."""
        templates = (
            reverse("posts:index"),
            reverse("posts:profile", kwargs={"username": self.post.author}),
        )
        for url in templates:
            with self.subTest(url):
                response = self.client.get(url)
                obj = response.context["page_obj"][0]
                self.assertEqual(obj.image, self.post.image)

    def test_image_in_post_detail_page(self):
        """Картинка передается на страницу post_detail."""
        response = self.client.get(
            reverse("posts:post_detail", kwargs={"post_id": self.post.id})
        )
        obj = response.context["post"]
        self.assertEqual(obj.image, self.post.image)

    def test_image_in_page(self):
        """Проверяем что создается пост с картинкой"""
        posts_count = Post.objects.count()
        form_data = {"image": "posts/small.gif", "text": "Введите текст"}
        response = self.authorized_client.post(
            reverse("posts:post_create"), data=form_data, follow=True
        )
        self.assertRedirects(
            response, reverse(
                "posts:profile",
                kwargs={"username": self.user.username})
        )
        self.assertEqual(Post.objects.count(), posts_count + 1)
        self.assertTrue(Post.objects.filter(image=form_data["image"]).exists())
        self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_comments(self):
        test_comment = Comment.objects.count()
        response = self.authorized_client.post(self.url, self.form_data)
        self.assertRedirects(
            response,
            reverse("posts:post_detail", args=[self.post.id])
        )
        self.assertEqual(Comment.objects.count(), test_comment + 1)
        comment = Comment.objects.latest("id")
        self.assertEqual(comment.text, self.form_data["text"])
