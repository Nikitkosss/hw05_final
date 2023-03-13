from django import forms

from .models import Comment, Post


class PostForm(forms.ModelForm):

    class Meta:
        model = Post
        fields = ('text', 'group', 'image')
        label = {'text': 'Введите текст', 'group': 'Выберите группу'}
        help_text = {
            'text': 'Любой текст, который вы хотите разместить.',
            'group': 'Из уже существующих групп.',
        }


class CommentForm(forms.ModelForm):
    class Meta:
        model = Comment
        fields = ("text",)
