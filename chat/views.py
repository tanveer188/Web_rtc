# chat/views.py
from django.shortcuts import render

def room(request, room_name):
    return render(request, 'chat/room.html', {
        "chat_box_name": room_name
    })
