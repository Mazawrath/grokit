<div align="center">
  <img src="./misc/grokit.svg" alt="Logo" height="70" />
  <p><strong>Unofficial Forked Python client for Grok models</strong></p>
  <p>Original repository by EveripediaNetwork</p>
</div>
<br/>

<p align="center">
<!--     <a href="https://pypi.python.org/pypi/grokit/"><img alt="PyPi" src="https://img.shields.io/pypi/v/grokit.svg?style=flat-square"></a> -->
    <a href="https://github.com/EveripediaNetwork/grokit/blob/master/LICENSE"><img alt="License" src="https://img.shields.io/github/license/EveripediaNetwork/grokit.svg?style=flat-square"></a>
</p>

## Installation

```bash
pip install git+https://github.com/Mazawrath/grokit
```

## Usage
Import the `Grokit` class and create an instance:

```python
from grokit import Grokit

# You can set the X_AUTH_TOKEN, X_CSRF_TOKEN, and X_CLIENT_TRANSACTION_ID environment variables instead
grok = Grokit(
    auth_token='***',
    csrf_token='***',
    x_client_transaction_id='***'
)
```

## Generate Text

```python
response = grok.generate(
    prompt='Who are you?',
    model_id='grok-3'
)
print(response.message)  # Access the generated response text
```

## Generate Images

### Upload an image and generate a response
```python
response = grok.generate(
    prompt='Describe this image.',
    attachments=['https://example.com/image.jpg']
)
print(response.message)  # Access the generated response text
```

### Generate an image URL
```python
response = grok.generate(
    prompt='An astronaut riding a horse.',
    model_id='grok-2',
)
print(response.attachments)  # List of generated image URLs
```

### Upload an image to edit and generate a response
```python
response = grok.generate(
    prompt='Make this image look like a painting.',
    attachments=['https://example.com/image.jpg'],
    edit_attachment=True
)
print(response.message)  # Access the generated response text
```

In this case, the first image in the `attachments` list will be used for editing. The `edit_attachment` parameter must be set to `True` to enable image editing.

## Download Images

### Download an image by ID or URL
You can download an image using its ID or URL:

```python
# Download by image ID
response = grok.download_image(123456789)

# Download by image URL
response = grok.download_image('https://ton.x.com/i/ton/data/grok-attachment/123456789')

# Save the image to a file
with open('downloaded_image.jpg', 'wb') as f:
    f.write(response.content)
```

The `download_image` method accepts either an image ID (integer) or a full image URL (string). The response contains the image data, which can be saved to a file.

## Credentials

To obtain the necessary credentials for using Grokit, follow these steps:

1. Log in to [x.com](https://x.com) with a Premium account.

2. Open your browser's Developer Tools.

3. Navigate to the Network tab in the Developer Tools.

4. Load [x.com/i/grok](https://x.com/i/grok) in your browser.

5. Type anything in the textbox and send it.

6. In the Network tab, look for the `POST` request to `https://grok.x.com/2/grok/add_response.json`.

7. Click on this request to view its details.

8. In the Headers section, find the "Cookie" header under Request Headers.

9. From the cookie string, extract the following values:
   - `ct0`: This is your csrf token
   - `auth_token`: This is your auth token

10. In the Headers section, find the `x-client-transaction-id` under Request Headers.