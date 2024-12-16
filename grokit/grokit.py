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
    def __init__(self, conversation_id: str, conversation_history: list, response: str, image_responses: Optional[list] = None):
        self.conversation_id = conversation_id
        self.response = response
        self.conversation_history = conversation_history
        self.image_response = image_responses or []


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
        conversation_history: list = [],
        conversation_id: Optional[str] = None,
        system_prompt_name: str = '',
        model_id: Union[GrokModels, str] = GrokModels.GROK_2_MINI,
    ) -> GrokResponse:
        conversation_id = self._ensure_conversation_id(conversation_id)
        
        conversation_history.append({
            "message": prompt,
            "sender": 1
        })

        # Collect all messages and image URLs
        full_message = []
        image_responses = []

        for response in self._stream_response(conversation_id, conversation_history, system_prompt_name, model_id):
            if response['type'] == 'image':
                image_responses.append(response['content'])
            elif response['type'] == 'text':
                full_message.append(response['content'])
                
        conversation_history.append({
            "message": full_message,
            "sender": 2,
            "fileAttachments": []
        })
        
        for image in image_responses:
            conversation_history[len(conversation_history) - 1]["fileAttachments"].append({
                "fileName": "the file"
            })

        return GrokResponse(
            conversation_id=conversation_id,
            conversation_history=conversation_history,
            response=''.join(full_message),
            image_responses=image_responses  # A list of image URLs
        )

    def stream(
        self,
        message: str,
        conversation_id: Optional[str] = None,
        system_prompt_name: str = '',
        model_id: Union[GrokModels, str] = GrokModels.GROK_2_MINI,
    ) -> Generator[str, None, None]:
        conversation_id = self._ensure_conversation_id(conversation_id)
        yield from self._stream_response(
            conversation_id,
            message,
            system_prompt_name,
            model_id,
        )

    def download_image(self, input_data):
        # Check if the input is an integer (ID) or a string (URL)
        if isinstance(input_data, int):
            # If it's an integer, use it directly as the image ID
            image_id = input_data
        elif isinstance(input_data, str):
            # If it's a URL, extract the ID from the URL
            image_id = input_data.split('/')[-1]
        else:
            raise ValueError("Input must be either an image ID (int) or an image URL (str)")
        # Call _get_image with the extracted ID
        return self._get_image(image_id)

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

    def _stream_response(
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
            json=payload,
            stream=True,
        )

        if response.status_code == 200:
            yield from self._process_response_stream(response)
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
            print('Error making request: {}'.format(response.text))
            return None

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
                    event = chunk['result'].get('event', {})
                    image_update = event.get('imageAttachmentUpdate', {})
                    if 'imageUrl' in image_update and image_update.get('progress') == 100:
                        yield {'type': 'image', 'content': image_update['imageUrl']}
                    # Extract regular messages
                    elif 'message' in chunk['result']:
                        yield {'type': 'text', 'content': chunk['result']['message']}

