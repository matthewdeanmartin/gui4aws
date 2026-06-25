"""Metadata for gui4aws."""

__all__ = [
    "__credits__",
    "__dependencies__",
    "__description__",
    "__keywords__",
    "__license__",
    "__readme__",
    "__requires_python__",
    "__status__",
    "__title__",
    "__version__",
]

__title__ = "gui4aws"
__version__ = "0.0.1"
__description__ = "Tkinter GUI for AWS"
__readme__ = "README.md"
__credits__ = [{"name": "Matthew Martin", "email": "matthewdeanmartin@gmail.com"}]
__keywords__ = ["gui4aws", "aws", "tkinter", "gui"]
__license__ = "MIT"
__requires_python__ = ">=3.10"
__status__ = "3 - Alpha"
__dependencies__ = ["boto3>=1.35.0", "keyring>=25.0.0", "tomli>=2.4.1 ; python_full_version < '3.11'"]
