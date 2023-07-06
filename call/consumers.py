import json
from channels.generic.websocket import AsyncWebsocketConsumer
from django.contrib.auth.models import User
from asgiref.sync import sync_to_async
import asyncio


class CallConsumer(AsyncWebsocketConsumer):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.call_answered = False  # Initialize call answered flag

    async def connect(self):
        if self.scope["user"].is_anonymous:
            # Reject the connection if the user is not authenticated
            await self.send(json.dumps({
                'type': 'login_first',
                'data': {
                    'message': "Connection Failed"
                }
            }))
            await self.close()
        else:
            # Connection accepted, store the user object for later use
            self.user = self.scope["user"]
            self.my_name = self.user.username
            await self.accept()

            # Join room
            await self.channel_layer.group_add(self.my_name, self.channel_name)

            await self.send(json.dumps({
                'type': 'connection',
                'data': {
                    'message': "Connected"
                }
            }))

    async def disconnect(self, close_code):
        # Leave room group
        await self.channel_layer.group_discard(self.my_name, self.channel_name)

    async def receive(self, text_data):
        text_data_json = json.loads(text_data)
        eventType = text_data_json['type']

        if eventType == 'call':
            name = text_data_json['data']['name']
            try:
                await sync_to_async(User.objects.get)(username=name)

                print(self.my_name, "is calling", name)
                if await self._has_group(name):
                    # Notify the callee by sending an event to the group with the callee's name
                    await self.channel_layer.group_send(
                        name, {
                            'type': 'call_received',
                            'data': {
                                'caller': self.my_name,
                                'rtcMessage': text_data_json['data']['rtcMessage']
                            }
                        })
                    asyncio.create_task(self.call_limit(name))
                else:
                    # Handle the case when no group with the caller exists
                    await self.send(json.dumps({
                        'type': 'call_offline',
                    }))
            except User.DoesNotExist:
                await self.close()

        if eventType == 'answer_call':
            caller = text_data_json['data']['caller']
            await self.channel_layer.group_send(
                caller, {
                    'type': 'handle_call_answered',
                    'data': {
                        'rtcMessage': text_data_json['data']['rtcMessage']
                    }
            })
            self.call_answered = True

        if eventType == 'reject_call':
            print('Call Rejected by', self.my_name)
            caller = text_data_json['otherUser']
            await self.channel_layer.group_send(caller, {
                'type': 'call_rejected',
            })
            self.call_answered = True

        if eventType == 'ICEcandidate':
            user = text_data_json['data']['user']
            await self.channel_layer.group_send(
                user, {
                    'type': 'ICEcandidate',
                    'data': {
                        'rtcMessage': text_data_json['data']['rtcMessage']
                    }
                })

    async def call_received(self, event):
        print('Call received by', self.my_name)
        await self.send(json.dumps({
            'type': 'call_received',
            'data': event['data']
        }))
        asyncio.create_task(self.call_limit(self.my_name))

    async def call_limit(self, user):
        timer_task = await asyncio.sleep(20)
        try:
            if not self.call_answered:
              print("not answered for",self.my_name)
              await self.send(json.dumps({
                    'type': 'call_not_answered'
                }))
        except asyncio.CancelledError:
            pass

    async def call_rejected(self, event):
        await self.send(json.dumps({
            'type': 'call_rejected'
        }))
        self.call_answered = True
    async def handle_call_answered(self, event):
        print(self.my_name, "'s call answered")
        await self.send(json.dumps({
            'type': 'call_answered',
            'data': event['data']
        }))
        self.call_answered = True  # Set call answered flag

    async def ICEcandidate(self, event):
        await self.send(json.dumps({
            'type': 'ICEcandidate',
            'data': event['data']
        }))

    async def _has_group(self, group_name):
        """
        Helper method to check if a group exists.
        """
        groups = self.channel_layer.groups
        return group_name in groups
