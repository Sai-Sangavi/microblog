# Welcome to Microblog!

This is an example application featured in my [Flask Mega-Tutorial](https://blog.miguelgrinberg.com/post/the-flask-mega-tutorial-part-i-hello-world). See the tutorial for instructions on how to work with it.

The version of the application featured in this repository corresponds to the 2024 edition of the Flask Mega-Tutorial. You can find the 2018 and 2021 versions of the code [here](https://github.com/miguelgrinberg/microblog-2018). And if for any strange reason you are interested in the original code, dating back to 2012, that is [here](https://github.com/miguelgrinberg/microblog-2012).

## Video upload settings

- `VIDEO_MAX_BYTES` — largest video a member can attach to a post, in bytes (default `524288000`, 500 MB). The proxy's body limit (for example nginx `client_max_body_size`) must allow slightly more than this.
- `VIDEO_UPLOAD_DIR` — directory where uploaded videos are stored (default `uploads/` in the repository). In production it must be writable, durable and shared by all web instances.

## Deployment notes

- Restart the app after changing `config.py`.
