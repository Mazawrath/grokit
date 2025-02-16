#!/usr/bin/env python
# -*- coding: utf-8 -*-

import requests
import json
from typing import Optional, Generator, Dict, Any, Union
from enum import Enum
from os import environ as env


class GrokModels(Enum):
    GROK_2 = 'grok-2'
    GROK_2A = 'grok-2a'
    GROK_2_MINI = 'grok-2-mini'

class GrokResponse:
    def __init__(self, conversation_id: str, conversation_history: list, response: str, limited: bool, attachments: Optional[list] = None):
        self.conversation_id = conversation_id
        self.conversation_history = conversation_history
        self.response = response
        self.limited = limited
        self.attachments = attachments or []


class Grokit:
    print_debug = False

    BEARER_TOKEN = (
        'AAAAAAAAAAAAAAAAAAAAANRILgAAAAAAnNwIzUejRCOuH5E6I8xnZz4puTs'
        '%3D1Zv7ttfk8LF81IUq16cHjhLTvJu4FA33AGWWjCpTnA'
    )

    def __init__(
        self,
        auth_token: Optional[str] = None,
        csrf_token: Optional[str] = None,
        print_debug: bool = False
    ):
        self.auth_token = auth_token or env.get('X_AUTH_TOKEN')
        self.csrf_token = csrf_token or env.get('X_CSRF_TOKEN')
        self._validate_tokens()
        self.cookie = self._create_cookie()
        self.headers = self._create_headers()
        self.print_debug = print_debug

    def _validate_tokens(self) -> None:
        if not self.auth_token or not self.csrf_token:
            raise ValueError('X_AUTH_TOKEN and X_CSRF_TOKEN must be provided')

    def _create_cookie(self) -> str:
        return 'auth_token={0}; ct0={1};'.format(
            self.auth_token,
            self.csrf_token,
        )

    def _create_headers(self) -> Dict[str, str]:
        return {
            'X-Csrf-Token': self.csrf_token,
            'authorization': 'Bearer {}'.format(self.BEARER_TOKEN),
            'Content-Type': 'application/json',
            'Cookie': self.cookie,
        }

    def create_conversation(self) -> Optional[str]:
        url = ('https://x.com/i/api/graphql/UBIjqHqsA5aixuibXTBheQ/'
               'CreateGrokConversation')
        payload = {
            'variables': {},
            'queryId': 'UBIjqHqsA5aixuibXTBheQ',
        }

        response = self._make_request(url, payload)
        if response and 'data' in response:
            return (
                response['data']['create_grok_conversation']['conversation_id']
            )
        return None

    def generate(
        self,
        prompt: str,
        attachments: list = [],
        conversation_history: Optional[list] = None,
        conversation_id: Optional[str] = None,
        system_prompt_name: str = '',
        model_id: Union[GrokModels, str] = GrokModels.GROK_2_MINI,
    ) -> GrokResponse:    
        if conversation_history is None:
            conversation_history = []  # Initialize a new list if None is passed

        conversation_id = self._ensure_conversation_id(conversation_id)
        
        conversation_history.append({
            "message": prompt,
            "sender": 1
        })

        # Collect all messages and image URLs
        full_message = []
        image_attachments = []
        image_urls = []
        limited = False

        for response in self._get_response(conversation_id, conversation_history, system_prompt_name, model_id):
            if response['type'] == 'image':
                image_attachments.append(response['value'])
                image_urls.append("https://ton.x.com/i/ton/data/grok-attachment/" + response['value']['mediaIdStr'])
            elif response['type'] == 'content':
                full_message.append(response['value'])
            elif response['type'] == 'responseType':
                # Apparently 'error' shows up when you reach the limit for image generation too.
                if response['value'] == "limiter" or response['value'] == "error":
                    limited = True
                
        conversation_history.append({
            "message": ''.join(full_message),
            "sender": 2,
            "fileAttachments": []
        })
        
        for image in image_attachments:
            conversation_history[len(conversation_history) - 1]["fileAttachments"].append({
                "fileName": image['fileName'],
                "mimeType": image['mimeType'],
                "mediaId": image['mediaId'],
                "imageUrl": image['imageUrl']
            })

        return GrokResponse(
            conversation_id=conversation_id,
            conversation_history=conversation_history,
            limited=limited,
            response=''.join(full_message),
            attachments=image_urls  # A list of image URLs
        )
  
    def upload_image(self, url: str) -> str:
        photo = requests.get("https://cdn.discordapp.com/attachments/1069880674330357770/1317023124927156274/image3.png?ex=675e7e5e&is=675d2cde&hm=c58f673030ec1f8eac3401c194494043e58b7d5690af300ac01df3fb33cd4ac8&")
        print(photo.raw)
        response = requests.post("https://x.com/i/api/2/grok/attachment.json", headers=self.headers, data=photo.raw)
        print(response.status_code)
        print(response.json())


    def _get_image(self, image_id: int):
        # Ensure the ID is a string for concatenation in the URL
        url = "https://ton.x.com/i/ton/data/grok-attachment/" + str(image_id)
        response = requests.get(url, headers=self.headers)
        return response

    def _ensure_conversation_id(self, conversation_id: Optional[str]) -> str:
        if not conversation_id:
            conversation_id = self.create_conversation()
            if not conversation_id:
                raise ValueError('Failed to create conversation')
        return conversation_id

    def _get_response(
        self,
        conversation_id: str,
        conversation_history: list,
        system_prompt_name: str,
        model_id: Union[GrokModels, str],
    ) -> Generator[dict, None, None]:
        url = 'https://api.x.com/2/grok/add_response.json'
        payload = self._create_add_response_payload(
            conversation_id,
            conversation_history,
            system_prompt_name,
            model_id,
        )

        response = requests.post(
            url,
            headers=self.headers,
            json=payload
        )

        if response.status_code == 200:
            return self._process_response_stream(response)
        else:
            raise RuntimeError(f"Error adding response: {response.text}")

    def _make_request(
        self,
        url: str,
        payload: Dict[str, Any],
    ) -> Optional[Dict[str, Any]]:
        response = requests.post(url, headers=self.headers, json=payload)
        if response.status_code == 200:
            return response.json()
        else:
            error_response = json.loads(response.text)
            raise Exception(error_response)

    def _create_add_response_payload(
        self,
        conversation_id: str,
        conversation_history: list,
        system_prompt_name: str,
        model_id: Union[GrokModels, str],
    ) -> Dict[str, Any]:
        return {
            'responses': conversation_history,
            'imageGenerationCount': 4,
            'systemPromptName': system_prompt_name,
            'grokModelOptionId': (
                model_id.value if isinstance(model_id, GrokModels)
                else model_id
            ),
            'conversationId': conversation_id,
        }

    def _process_response_stream(self, response: requests.Response) -> Generator[dict, None, None]:
        for line in response.iter_lines():
            if line:
                chunk = json.loads(line)
                if self.print_debug:
                    print(chunk)
                if 'result' in chunk:
                    # Check for image updates
                    if 'imageAttachment' in chunk['result']:
                        yield {'type': 'image', 'value': chunk['result']['imageAttachment']}
                    # Extract regular messages
                    if 'message' in chunk['result']:
                        yield {'type': 'content', 'value': chunk['result']['message']}
                    if 'responseType' in chunk['result']:
                        yield {'type': 'responseType', 'value': chunk['result']['responseType']}

