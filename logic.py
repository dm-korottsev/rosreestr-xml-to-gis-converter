import re
import json
import csv
from zipfile import is_zipfile, ZipFile

__author__ = "Dmitry S. Korottsev"
__copyright__ = "Copyright 2020"
__credits__ = []
__license__ = "GPL v3"
__version__ = "1.3"
__maintainer__ = "Dmitry S. Korottsev"
__email__ = "dm-korottev@yandex.ru"
__status__ = "Development"


def get_dict_from_csv(filepath):
    """
    создаёт словарь Python из csv-файла c 2-мя столбцами и разделителем '|'
    :param filepath: str
    :return: dict
    """
    with open(filepath, "r", newline="") as file:
        reader = csv.reader(file, delimiter='|', quoting=csv.QUOTE_NONE)
        dic = {row[0]: row[1] for row in reader}
    return dic


def write_settings(key, value):
    """
    сохраняет настройки программы в файл 'settings.json'
    """
    with open('settings.json', 'r') as f:
        sd = json.load(f)
    sd[key] = value
    with open('settings.json', 'w') as f:
        json.dump(sd, f, sort_keys=True, indent=4, ensure_ascii=False)


def get_settings(key):
    """
    возвращает значение параметра настройки программы по указанному ключу, сохранённое в файле 'settings.json'
    :param key: str
    """
    with open('settings.json', 'r') as f:
        sd = json.load(f)
    return sd[key]


def to_shorten_a_long_name(names):
    """
    сокращает слова и словосочетания в соответствии со словарём сокращений, заданным в файле 'replace.csv'
    :param names: list or str
    :return: list or str
    """
    dictionary_of_abbreviations = get_dict_from_csv('replace.csv')
    if isinstance(names, list):
        for old_name in dictionary_of_abbreviations:
            if names:
                for item in names:
                    temp = item
                    i_of_it = names.index(item)
                    new_item = re.sub(old_name, dictionary_of_abbreviations[old_name], temp, flags=re.IGNORECASE)
                    names[i_of_it] = new_item
    if isinstance(names, str):
        for old_name in dictionary_of_abbreviations:
            names = re.sub(old_name, dictionary_of_abbreviations[old_name], names, flags=re.IGNORECASE)
    return names


def gauss_area(polygon_points):
    """
    Формула площади Гаусса, определяет площадь простого многоугольника по декартовым координатам на плоскости
    В правой системе координат положительный знак площади указывает направление точек против часовой стрелки,
    отрицательный - направление точек по часовой стрелке
    :return: float
    """
    one = sum([polygon_points[i][0] * polygon_points[i + 1][1] for i in range(len(polygon_points) - 1)])
    two = sum([polygon_points[i][1] * polygon_points[i + 1][0] for i in range(len(polygon_points) - 1)])
    return (two - one) / 2


def extract_all_zipfiles(names_of_zipfiles, folder):
    """
    Распаковывает все указанные zip-архивы в указанной папке. Входящие аргументы: список имён архивов, которые надо
    распаковать и полный путь к папке, в которой они лежат.
    :param names_of_zipfiles: list
    :param folder: str
    """
    for zf in names_of_zipfiles:
        if is_zipfile(folder + '//' + zf):
            with ZipFile(folder + '//' + zf, 'r') as z:
                z.extractall(folder)
