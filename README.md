
# ScrapyNotebook
  **ScrapyNotebok** - расширение **IPython** для работы со scrapy.
  Работает со Scrapy, начиная с версии 1.0 и новыми версиями Jupyter.
  Если необходима работа со старыми версиями, создайте issue, я верну поддержку старых версий.

## Расширение для Scrapy
  ScrapyNotebook состоит из двух частей:
  1. `ScrapyNotebook.rpyc_service` - расширение **Scrapy**, необходимое для связи с **IPython**
  2. `ScrapyNotebookExt` - само расширение **IPython**


### rpyc_service
  Это расширение необходимо для подключения **IPython** к уже действующему Scrapy-парсеру и управления парсером. Т. к. **Scrapy** можно запустить и через **IPython**, не является обязательным для установки в Scrapy-парсер.


### ScrapyNotebookExt
  Это расширение **IPython** предоставляет доступ к работающего Scrapy-парсера и даёт минимальные инструменты для управления парсером.


## Install
  Вообще предполагается, что расширение для **IPython** состоит из одного py-файла, который просто копируется в папку для расширений с помощью команды `%install_ext`. Однако, **ScrapyNotebook** состоит из нескольких файлов (так проще и удобней) и частей, связанных общим кодом, то оно устанавливается как полноценный модуль. А в качестве расширения для **IPython** и py-файла для установки выступает `ScrapyNotebookExt.py`, который просто ре-экспортирует нужные функции из главного модуля `scrapy_side.py`

* Install **ScrapyNotebook** package

   `pip install https://github.com/horpto/ScrapyNotebook/zipball/master`

* Install ScrapyNotebookExt (in **IPython**)

    `%install_ext ScrapyNotebook` or `%install_ext https://rawgit.com/horpto/ScrapyNotebook/master/ScrapyNotebook/ScrapyNotebookExt.py`

* Install pygments (optional; used to highlight python code)

  `pip install pygments`

* Install rpyc_service (optional)
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
## Magic commands
Смотри examples.ipynb

|Команда       |Описание                                                     |
|--------------|-------------------------------------------------------------|
|%scrapy_list  |Список действующих scrapy                                    |
|%scrapy_embed |Запустить локальный scrapy (как scrapy shell)                |
|%scrapy_attach|Прикрепиться к удаленному scrapy                             |
|%process_shell|Запустить код на стороне scrapy (то есть удаленно)           |
|%scrapy_stop  |полностью остановить scrapy                                  |
|%scrapy_pause |Приостановить scrapy                                         |
|%scrapy_resume|Возобновить выполнение scrapy                                |
|%common_stats |Общая статистика                                             |
|%spider_stats |Статистика для паука scrapy                                  |
|%print_source |Напечатать возможный исходник данного метода, класса, функции|
|%set_method   |Добавить метод в класс                                       |
------------------------------------------------------------------------------

## Добавляемые переменные
## Variables added to scope:
|Переменная|Значение                           |
|----------|-----------------------------------|
|engine    |ExecutionEngine                    |
|spider    |Текущий паук                       |
|crawler   |Crawler                            |
|extensions|ExtensionManager                   |
|stats     |общая статистика                   |
|spiders   |SpiderManager                      |
|settings  |настройки crawler                  |
|est       |Напечатать состояние engine        |
|prefs     |Напечатать текущее состояние пауков|
|hpy       |heapy object from guppy            |
------------------------------------------------
