import re
import json
import csv


def get_dict_from_csv(filepath):
    with open(filepath, "r", newline="") as file:
        reader = csv.reader(file, delimiter='|', quoting=csv.QUOTE_NONE)
        dic = {row[0]: row[1] for row in reader}
    return dic


def write_settings(key, value):
    with open('settings.json', 'r') as f:
        sd = json.load(f)
    sd[key] = value
    with open('settings.json', 'w') as f:
        json.dump(sd, f, sort_keys=True, indent=4, ensure_ascii=False)


def get_settings(key):
    with open('settings.json', 'r') as f:
        sd = json.load(f)
    return sd[key]


def settings_from_json():
    with open('settings.json', 'r') as f:
        sd = json.load(f)
    return sd


def to_shorten_a_long_name(names):
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
    '''
    Формула площади Гаусса, определяет площадь простого многоугольника по декартовым координатам на плоскости
    В правой системе координат положительный знак площади указывает направление точек против часовой стрелки,
    отрицательный - направление точек по часовой стрелке
    '''
    one = sum([polygon_points[i][0] * polygon_points[i + 1][1] for i in range(len(polygon_points) - 1)])
    two = sum([polygon_points[i][1] * polygon_points[i + 1][0] for i in range(len(polygon_points) - 1)])
    return (two - one) / 2
