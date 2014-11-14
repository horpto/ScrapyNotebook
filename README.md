
# ScrapyNotebook
  **ScrapyNotebok** - расширение **IPython** для работы со scrapy.

## Расширение для Scrapy
  ScrapyNotebook состоит из двух частей:
  1. `ScrapyNotebook.rpyc_service` - расширение **Scrapy**, необходимое для связи с **IPython**
  2. `ScrapyNotebookExt` - само расширение **IPython**


### rpyc_service
  Это расширение необходимо для подключения **IPython** к уже действующему Scrapy-парсеру и управления парсером. Т. к. **Scrapy** можно запустить и через **IPython**, неявляется обязательным для установки в Scrapy-парсер.


### ScrapyNotebookExt
  Это расширение **IPython** предоставляет  доступ к работающего Scrapy-парсера и даёт минимальные инструменты для управления парсером.


## Installing
  Вообще предполагается, что расширение для **IPython** состоит из одного py-файла, который просто копируется в папку для расширений с помощью команды `%install_ext`. Однако, **ScrapyNotebook** состоит из нескольких файлов(так проще и удобней) и частей, связанных общим кодом, то оно устанавливается как полноценный модуль. А в качестве расширения для **IPython** и py-файла для установки выступает `ScrapyNotebookExt.py`, который просто ре-экспортирует нужные функции из главного модуля `scrapy_side.py`

* Install **ScrapyNotebook** packet

   `pip install git+https://github.com/horpto/ScrapyNotebook.git`

* Install ScrapyNotebookExt(in **IPython**)

   `%install_ext https://rawgit.com/horpto/ScrapyNotebook/master/ScrapyNotebook/ScrapyNotebookExt.py`


* Install rpyc_service(optional)
  ```python
  # add field in EXTENSIONS in config.py
  EXTENSIONS = {
    'ScrapyNotebook.rpyc_service.RPyCFactory' :500,

    # other extensions ...
  }

  # Parameters of rpyc_service extensions
  RPYCSERVICE_ENABLED = 1 # enabled\disabled
  RPYCSERVICE_PORT = [13113, 13163] # default portrange
  RPYCSERVICE_HOST = '0.0.0.0' # default host
  ```

## Магические команды
  Смотри examples.ipynb
