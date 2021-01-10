from abc import ABC
import re
import json
import xml.etree.ElementTree as ElT
from logic import get_dict_from_csv, gauss_area

__author__ = "Dmitry S. Korottsev"
__copyright__ = "Copyright 2021"
__credits__ = []
__license__ = "GPL v3"
__version__ = "1.5"
__maintainer__ = "Dmitry S. Korottsev"
__email__ = "dm-korottev@yandex.ru"
__status__ = "Development"


class AbstractOCC(ABC):
    def __init__(self, xml_file_path, settings, root, dop):
        self.xml_file_path = xml_file_path
        self.type = "Объект капитального строительства"
        self._root = root
        self._dop = dop
        self._realty = None
        self._extract_object_right = None
        self._namespaces = dict()
        self._adr = ''
        self._spat = ''
        self._settings = settings
        self.codes_of_rf_regions = get_dict_from_csv('region.csv')  # коды регионов РФ
        self.status_classifier = get_dict_from_csv('status.csv')  # коды статусов
        self.rights_classifier = get_dict_from_csv('right.csv')  # коды видов прав
        self.encumbrance_classifier = get_dict_from_csv('encumbrance.csv')  # коды видов ограничений (обременений)

    @staticmethod
    def create_an_occ_object(xml_file_path: str):
        """
        Определяет xml-схему выписки и возвращает экземпляр соответствующего ей класса.
        В случае, если xml-схема выписки из Росреестра неизвестна, возвращает None.
        """
        tree = ElT.parse(xml_file_path)
        root = tree.getroot()
        d1 = '{urn://x-artefacts-rosreestr-ru/outgoing/kvoks/3.0.1}'
        d2 = '{urn://x-artefacts-rosreestr-ru/outgoing/kpoks/4.0.1}'
        with open('settings.json', 'r') as f:
            sd = json.load(f)
        if root.find(d1 + 'Realty') is not None:
            return ObjectOfCapitalConstructionKVOKS(xml_file_path, sd, root, d1)
        elif root.find(d2 + 'Realty') is not None:
            return ObjectOfCapitalConstructionKPOKS(xml_file_path, sd, root, d2)
        else:
            return None

    @property
    def _real_estate_object(self):
        building = self._realty.find(self._dop + 'Building')
        flat = self._realty.find(self._dop + 'Flat')
        if building is not None:
            return building
        elif flat is not None:
            return flat
        else:
            return None

    @property
    def parent_cad_number(self):
        """
        возвращает кадастровый номер объекта недвижимости
        :return: str
        """
        real_estate_object = self._real_estate_object
        if real_estate_object is not None:
            cad_number = real_estate_object.get('CadastralNumber')
        else:
            cad_number = ''
        return cad_number

    @property
    def entry_parcels(self):
        cadastral_numbers = []
        return cadastral_numbers

    @property
    def area(self):
        """
        возвращает площадь объекта недвижимости
        :return: str
        """
        real_estate_object = self._real_estate_object
        if real_estate_object is not None:
            t_area = real_estate_object.find(self._dop + 'Area')
            area = t_area.text
        else:
            area = ''
        return area

    @property
    def status(self):
        """
        возвращает статус объекта недвижимости (например: учтённый, временный и т.д.)
        :return: str
        """
        real_estate_object = self._real_estate_object
        if real_estate_object is not None:
            st = self.status_classifier[real_estate_object.get('State')]
        else:
            st = ''
        return st

    @property
    def address(self):
        """
        возвращает адрес объекта недвижимости в человекочитаемом виде
        :return: str
        """
        t_address = None
        address_note = None
        real_estate_object = self._real_estate_object
        if real_estate_object is not None:
            t_address = real_estate_object.find(self._dop + 'Address')
        if t_address is not None:
            address_note = t_address.find(self._adr + ':Note', self._namespaces)
        if address_note is not None:
            address = address_note.text
            if address == ',':
                address = ''
        else:
            address = ''
            if t_address is not None:
                region = t_address.find(self._adr + ':Region', self._namespaces)
                district = t_address.find(self._adr + ':District', self._namespaces)
                urban_district = t_address.find(self._adr + ':UrbanDistrict', self._namespaces)
                locality = t_address.find(self._adr + ':Locality', self._namespaces)
                street = t_address.find(self._adr + ':Street', self._namespaces)
                level_1 = t_address.find(self._adr + ':Level1', self._namespaces)
                level_2 = t_address.find(self._adr + ':Level2', self._namespaces)
                level_3 = t_address.find(self._adr + ':Level3', self._namespaces)
                apartment = t_address.find(self._adr + ':Apartment', self._namespaces)
                if region is not None:
                    address = address + self.codes_of_rf_regions[region.text]
                if district is not None:
                    address = address + ', ' + district.get('Name') + ' ' + district.get('Type')
                if urban_district is not None:
                    address = address + ', ' + urban_district.get('Name') + ' ' + urban_district.get('Type')
                if locality is not None:
                    address = address + ', ' + locality.get('Type') + ' ' + locality.get('Name')
                if street is not None:
                    address = address + ', ' + street.get('Name') + ' ' + street.get('Type')
                if level_1 is not None:
                    address = address + ', ' + level_1.get('Type') + ' ' + level_1.get('Value')
                if level_2 is not None:
                    address = address + ', ' + level_2.get('Type') + ' ' + level_2.get('Value')
                if level_3 is not None:
                    address = address + ', ' + level_3.get('Type') + ' ' + level_3.get('Value')
                if apartment is not None:
                    address = address + ', ' + apartment.get('Type') + ' ' + apartment.get('Value')
        return address

    @property
    def district_name(self):
        district_name = ''
        real_estate_object = self._real_estate_object
        if real_estate_object is not None:
            location = real_estate_object.find(self._dop + 'Address')
            if location is not None:
                district = location.find(self._adr + ':District', self._namespaces)
                if district is not None:
                    district_name = district.get('Name')
        return district_name

    @property
    def category(self):
        return '-'

    @property
    def permitted_use_by_doc(self):
        return '-'

    @property
    def cadastral_cost(self):
        """
        возвращает кадастровую стоимость объекта недвижимости (в рублях)
        :return: str
        """
        real_estate_object = self._real_estate_object
        if real_estate_object is not None:
            cad_cost = real_estate_object.find(self._dop + 'CadastralCost')
            cad_cost_value = cad_cost.get('Value')
        else:
            cad_cost_value = ''
        return cad_cost_value

    @property
    def owner(self):
        """
        возвращает список правообладателей (вид права и лицо, владеющее этим правом)
        :return: str
        """
        type_sobstv = ''
        list_dolei = []
        list_type_sobstv = []
        list_owner = []
        set_dolevikov = set()
        list_dolevikov = []
        cell_owner = []
        doli_two_persons = []
        list_dolevikov_new = []
        list_sovm_sobsv = []
        vse_doli_u_odnogo_chel = []
        list_doli_ga = []
        cell_owner_doli_ga = []
        if self._extract_object_right is not None:
            for right in self._extract_object_right.findall(self._dop + 'ExtractObject/' +
                                                            self._dop + 'ObjectRight/' +
                                                            self._dop + 'Right'):
                for childs in right:
                    if childs.tag == self._dop + 'Registration':
                        sobstv = childs.find(self._dop + 'Type')
                        type_sobstv = self.rights_classifier[sobstv.text]
                        if sobstv.text == '001002000000':
                            type_sobstv = 'Долевая собственность'
                            doli_1 = childs.find(self._dop + 'ShareText')
                            doli_2 = childs.find(self._dop + 'Share')
                            if doli_1 is not None:
                                if not re.search(r"пропорциональн", doli_1.text):
                                    try:
                                        list_dolei.append(int(re.sub(r"[0-9]+/", '', doli_1.text)))
                                        doli_two_persons.append(doli_1.text)
                                    except:
                                        list_doli_ga.append(doli_1.text)
                            elif doli_2 is not None:
                                list_dolei.append(int(doli_2.get('Denominator')))
                                stroka = str(doli_2.get('Numerator')) + "/" + str(doli_2.get('Denominator'))
                                doli_two_persons.append(stroka)
                            list_type_sobstv.append(type_sobstv)
                        elif sobstv.text == '001003000000':
                            type_sobstv = 'Совместная собственность'
                            for right in self._extract_object_right.findall(self._dop + 'ExtractObject/' +
                                                                            self._dop + 'ObjectRight/' +
                                                                            self._dop + 'Right'):
                                proverka = right.find(self._dop + 'Registration/' + self._dop + 'Type')
                                if proverka is not None:
                                    if proverka.text == '001003000000':
                                        for childs in right:
                                            if childs.tag == self._dop + 'Owner':
                                                for child in childs:
                                                    if child.tag == self._dop + 'Person':
                                                        content_p = child.find(self._dop + 'Content')
                                                        nname = content_p.text
                                                        list_sovm_sobsv.append(nname)
                                                    if child.tag == self._dop + 'Organization':
                                                        names = child.find(self._dop + 'Content')
                                                        nname = names.text
                                                        nname = re.sub(", ИНН", " ИНН", nname)
                                                        list_sovm_sobsv.append(nname)
                                                    if child.tag == self._dop + 'Governance':
                                                        names = child.find(self._dop + 'Name')
                                                        nname = names.text
                                                        list_sovm_sobsv.append(nname)
                        else:
                            list_type_sobstv.append(self.rights_classifier[sobstv.text])
                    if childs.tag == self._dop + 'NoRegistration':
                        pass
                    if childs.tag == self._dop + 'Owner':
                        for child in childs:
                            if child.tag == self._dop + 'Person':
                                content_p = child.find(self._dop + 'Content')
                                nname = content_p.text
                                proverka = right.find(self._dop + 'Registration/' + self._dop + 'Type')
                                if proverka is not None:
                                    if proverka.text != '001003000000':
                                        list_owner.append(nname)
                            if child.tag == self._dop + 'Organization':
                                names = child.find(self._dop + 'Content')
                                nname = names.text
                                nname = re.sub(", ИНН", " ИНН", nname)
                                proverka = right.find(self._dop + 'Registration/' + self._dop + 'Type')
                                if proverka is not None:
                                    if proverka.text != '001003000000':
                                        list_owner.append(nname)
                            if child.tag == self._dop + 'Governance':
                                names = child.find(self._dop + 'Name')
                                nname = names.text
                                proverka = right.find(self._dop + 'Registration/' + self._dop + 'Type')
                                if proverka is not None:
                                    if proverka.text != '001003000000':
                                        list_owner.append(nname)
        if len(list_type_sobstv) == len(list_owner):
            for item in list_type_sobstv:
                i_of_it = list_type_sobstv.index(item)
                cell_owner.append(str(item + ' ' + list_owner[i_of_it]))
        for item in list_doli_ga:
            i_of_it = list_doli_ga.index(item)
            cell_owner_doli_ga.append(str(item + ' ' + list_owner[i_of_it]))
        #  если в обычных полях правообладатель не указан, то ищем в устаревших полях (из БД ГКН)
        if not cell_owner:
            rights_gkn = self._realty.find(self._dop + 'Rights')
            if rights_gkn is not None:
                for right_gkn in rights_gkn.findall(self._dop + 'Right'):
                    type_sob_gkn = right_gkn.find(self._dop + 'Type')
                    if type_sob_gkn is not None:
                        type_sobstv = self.rights_classifier[type_sob_gkn.text]
                        list_type_sobstv.append(type_sobstv)
                        if type_sobstv == 'Долевая собственность':
                            doli = right_gkn.find(self._dop + 'Share')
                            if doli is not None:
                                list_dolei.append(int(doli.get('Denominator')))
                                stroka = str(doli.get('Numerator')) + "/" + str(doli.get('Denominator'))
                                doli_two_persons.append(stroka)
                    person_gkn = right_gkn.find(self._dop + 'Owners/' + self._dop + 'Owner/' + self._dop + 'Person')
                    governance_gkn = right_gkn.find(self._dop + 'Owners/' + self._dop + 'Owner/' + self._dop +
                                                    'Governance')
                    organization_gkn = right_gkn.find(self._dop + 'Owners/' + self._dop + 'Owner/' + self._dop +
                                                      'Organization')
                    if person_gkn is not None:
                        family_name_gkn = person_gkn.find(self._dop + 'FamilyName')
                        first_name_gkn = person_gkn.find(self._dop + 'FirstName')
                        patronymic_gkn = person_gkn.find(self._dop + 'Patronymic')
                        if patronymic_gkn is not None:
                            patronymic_gkn = patronymic_gkn.text
                        else:
                            patronymic_gkn = ''
                        if family_name_gkn is not None:
                            family_name_gkn = family_name_gkn.text
                        else:
                            family_name_gkn = ''
                        if first_name_gkn is not None:
                            first_name_gkn = first_name_gkn.text
                        else:
                            first_name_gkn = ''
                        if family_name_gkn is not None and first_name_gkn is not None and patronymic_gkn is not None:
                            fio_gkn = family_name_gkn + ' ' + first_name_gkn + ' ' + patronymic_gkn
                        elif family_name_gkn is not None and first_name_gkn is not None:
                            fio_gkn = family_name_gkn + ' ' + first_name_gkn
                        else:
                            fio_gkn = None
                        if fio_gkn is not None and fio_gkn not in list_owner:
                            list_owner.append(fio_gkn)
                    elif organization_gkn is not None:
                        names_gkn = organization_gkn.find(self._dop + 'Name')
                        if names_gkn.text not in list_owner:
                            if names_gkn.text is not None:
                                list_owner.append(names_gkn.text)
                            else:
                                list_owner.append(' ')
                    elif governance_gkn is not None:
                        names_gkn = governance_gkn.find(self._dop + 'Name')
                        if names_gkn.text not in list_owner:
                            if names_gkn.text is not None:
                                list_owner.append(names_gkn.text)
                            else:
                                list_owner.append(' ')
            if len(list_type_sobstv) == len(list_owner):
                i_of_it = 0
                for item in list_type_sobstv:
                    cell_owner.append(item + ' ' + list_owner[i_of_it])
                    i_of_it += 1
            elif list_type_sobstv != [] and list_owner == []:
                for item in list_type_sobstv:
                    cell_owner.append(item)
            elif len(set(list_type_sobstv)) == 1 and len(list_owner) == 1:
                cell_owner.append(list_type_sobstv[0] + ' ' + list_owner[0])
        # Некоторые ФИО долевиков написаны строчными буквами, а некоторые - заглавными.
        # Чтобы посчитать количество уникальных ФИО, делаем все элементы списка заглавными буквами
        for item in list_owner:
            vremyanka = item.upper()
            set_dolevikov.add(vremyanka)
            list_dolevikov.append(vremyanka)
        # Для записи в итоговую таблицу приводим все ФИО долевиков к нормальному виду
        if 0 < len(list_dolevikov) < 3:
            for s_up in list_dolevikov:
                result = s_up.title()
                list_dolevikov_new.append(result)
        # Для участков, на которые не зарегистрированы права, указываем правообладателем администрацию района
        # (если включены соответствующие настройки программы)
        elif not cell_owner:
            if self._settings["adm_district"]:
                if re.search(r"[\w-]+ий", self.district_name):
                    match = re.search(r"[\w-]+ий", self.district_name)
                    name_r = match.group()
                    result = "Администрация " + re.sub('ий', 'ого', name_r + " района")
                    cell_owner.append(result)
                elif re.search(r"[\w-]+ой", self.district_name):
                    match = re.search(r"[\w-]+ой", self.district_name)
                    name_r = match.group()
                    result = "Администрация " + re.sub('ой', 'ого', name_r + " района")
                    cell_owner.append(result)
        if type_sobstv == 'Долевая собственность':
            if len(list_type_sobstv) == 1 and len(list_owner) == 1:
                return cell_owner[0]
            elif list_doli_ga:
                if len(list_doli_ga) == len(list_owner):
                    return 'Долевая собственность ' + ', '.join(cell_owner_doli_ga)
                else:
                    print('Необработанное исключение в файле ' + self.xml_file_path)
            elif list_dolei:
                try:
                    if len(list_dolevikov) > 2:
                        return type_sobstv + ' (' + str(max(list_dolei)) + ' долей; ' + str(
                            len(set_dolevikov)) + ' правообладателей)'
                    elif len(list_dolevikov) == 1:
                        return type_sobstv + ' ' + doli_two_persons[0] + ' ' + list_dolevikov_new[0]
                    else:
                        return (type_sobstv + ': ' + doli_two_persons[0] + ' ' + list_dolevikov_new[0] +
                                ', ' + doli_two_persons[1] + ' ' + list_dolevikov_new[1])
                except:
                    print('не удалось обработать файл: ' + self.xml_file_path)
            else:
                if len(set_dolevikov) > 0:
                    return type_sobstv + ' (' + str(len(set_dolevikov)) + ' правообладателей)'
        elif list_sovm_sobsv:
            if list_sovm_sobsv != list_owner:
                return 'Совместная собственность ' + ', '.join(list_sovm_sobsv) + ', ' + ', '.join(cell_owner)
            else:
                return 'Совместная собственность ' + ', '.join(list_sovm_sobsv)
        # случай, когда один человек собственник всех долей в праве + есть сервитут
        elif type_sobstv != 'Долевая собственность' and list_dolei != []:
            if len(list_dolei) > 2:
                return 'Долевая собственность ' + ' (' + str(
                    max(list_dolei)) + ' долей; ' + str(len(set_dolevikov)) + ' правообладателей)'
            else:
                dopzap = ''
                for dtp in doli_two_persons:
                    zap = 'Долевая собственность ' + str(dtp) + ' ' + str(
                        list_owner[doli_two_persons.index(dtp)]).title()
                    vse_doli_u_odnogo_chel.append(zap)
                if (len(list_owner) == len(doli_two_persons) + 1) and list_type_sobstv != []:
                    dopzap = ', ' + str(list_type_sobstv[0]) + ' ' + list_owner[len(list_owner) - 1]
                return ', '.join(vse_doli_u_odnogo_chel) + dopzap
        else:
            return ', '.join(cell_owner)

    @property
    def own_name_reg_numb_date(self):
        """
        возвращает вид права, номер регистрации и дату регистрации права на объект недвижимости
        :return: str
        """
        name_numb_date = []
        if self._extract_object_right is not None:
            for right in self._extract_object_right.findall(self._dop + 'ExtractObject/' +
                                                            self._dop + 'ObjectRight/' +
                                                            self._dop + 'Right'):
                for childs in right:
                    if childs.tag == self._dop + 'Registration':
                        name = childs.find(self._dop + 'Name')
                        if name is not None:
                            name_numb_date.append(name.text)
        if not name_numb_date:
            rights_gkn = self._realty.find(self._dop + 'Rights')
            if rights_gkn is not None:
                for right_gkn in rights_gkn.findall(self._dop + 'Right'):
                    type_sob_gkn = right_gkn.find(self._dop + 'Type')
                    name_sob_gkn = right_gkn.find(self._dop + 'Name')
                    rn_gkn = right_gkn.find(self._dop + 'Registration/' + self._dop + 'RegNumber')
                    rd_gkn = right_gkn.find(self._dop + 'Registration/' + self._dop + 'RegDate')
                    if type_sob_gkn is not None and rn_gkn is not None and rd_gkn is not None:
                        type_sobstv = self.rights_classifier[type_sob_gkn.text]
                        reg_number_gkn = rn_gkn.text
                        reg_date_gkn = rd_gkn.text
                        name_numb_date.append(type_sobstv + ' №' + reg_number_gkn + ' от ' + reg_date_gkn)
                    elif name_sob_gkn is not None and rn_gkn is not None:
                        name_sobstv = name_sob_gkn.text
                        reg_number_gkn = rn_gkn.text
                        name_numb_date.append(name_sobstv + '; ' + reg_number_gkn)
                    elif name_sob_gkn is not None:
                        name_sobstv = name_sob_gkn.text
                        name_numb_date.append(name_sobstv)
        if not name_numb_date:
            return ''
        else:
            return '; '.join(name_numb_date)

    @property
    def encumbrances(self):
        """
        возвращает список ограничений (обременений) прав и лиц, в пользу которых они установлены
        :return: str
        """
        obrem = ''
        set_obrem = set()
        list_arendatorov = []
        new_list_arendatorov = []
        doc = []
        if self._extract_object_right is not None:
            for right in self._extract_object_right.findall(self._dop + 'ExtractObject/' +
                                                            self._dop + 'ObjectRight/' +
                                                            self._dop + 'Right'):
                for childs in right:
                    if childs.tag == self._dop + 'Encumbrance':
                        name_obrem = childs.find(self._dop + 'Name')
                        obrem_name = name_obrem.text
                        obrem_text = ''
                        owner_obrem = childs.find(self._dop + 'Owner')
                        share_text = childs.find(self._dop + 'ShareText')
                        if share_text is not None:
                            obrem_text = ' (' + share_text.text + ')'
                        for child in childs.findall(self._dop + 'DocFound'):
                            content = child.find(self._dop + 'Content')
                            if content is not None:
                                if content.text not in doc:
                                    doc.append(content.text)
                        if owner_obrem is None:
                            if share_text is not None:
                                set_obrem.add(obrem_name + obrem_text)
                            else:
                                set_obrem.add(obrem_name)
                        else:
                            for child in owner_obrem:
                                if child.tag == self._dop + 'Person':
                                    nname = ''
                                    for names in child.findall(self._dop + 'FIO/'):
                                        nname += names.text + ' '
                                    if str(obrem_name + ' ' + nname) not in list_arendatorov:
                                        list_arendatorov.append(str(obrem_name + ' ' + nname + obrem_text))
                                if child.tag == self._dop + 'Organization':
                                    content = child.find(self._dop + 'Content')
                                    nname = content.text
                                    nname = re.sub(", ИНН", " ИНН", nname)
                                    if str(obrem_name + ' ' + nname) not in list_arendatorov:
                                        list_arendatorov.append(str(obrem_name + ' ' + nname + obrem_text))
                                if child.tag == self._dop + 'Governance':
                                    names = child.find(self._dop + 'Name')
                                    nname = names.text + ' '
                                    if str(obrem_name + ' ' + nname) not in list_arendatorov:
                                        list_arendatorov.append(str(obrem_name + ' ' + nname + obrem_text))
            if set_obrem is not set():
                if len(set_obrem) == 1:
                    for i in set_obrem:
                        obrem += i
                else:
                    c = 0
                    for i in set_obrem:
                        if c == 0:
                            obrem += i
                            c += 1
                        else:
                            obrem += '; ' + i
                            c += 1
                dop_ob = self._extract_object_right.find(self._dop + 'ExtractObject')
                if dop_ob is not None:
                    dop_obrem = dop_ob.find(self._dop + 'RightClaim')
                    if dop_obrem is not None:
                        if dop_obrem.text != 'данные отсутствуют':
                            obrem += ', ' + dop_obrem.text
        if not list_arendatorov:
            encumbrances_gkn = self._realty.find(self._dop + 'Encumbrances')
            if encumbrances_gkn is not None:
                for encumbrance_gkn in encumbrances_gkn.findall(self._dop + 'Encumbrance'):
                    type_obr_gkn = encumbrance_gkn.find(self._dop + 'Type')
                    name_obr_gkn_organiz = encumbrance_gkn.find(self._dop + 'OwnersRestrictionInFavorem/' +
                                                                self._dop + 'OwnerRestrictionInFavorem/' +
                                                                self._dop + 'Organization/' +
                                                                self._dop + 'Name')
                    obr_gkn_person = encumbrance_gkn.find(self._dop + 'OwnersRestrictionInFavorem/' +
                                                          self._dop + 'OwnerRestrictionInFavorem/' +
                                                          self._dop + 'Person')
                    if type_obr_gkn is not None and name_obr_gkn_organiz is not None:
                        type_name_enc_gkn = self.encumbrance_classifier[type_obr_gkn.text] + ' ' + \
                                            name_obr_gkn_organiz.text
                        if type_name_enc_gkn not in list_arendatorov:
                            list_arendatorov.append(type_name_enc_gkn)
                    if type_obr_gkn is not None and obr_gkn_person is not None:
                        family_name = obr_gkn_person.find(self._dop + 'FamilyName')
                        first_name = obr_gkn_person.find(self._dop + 'FirstName')
                        patronymic = obr_gkn_person.find(self._dop + 'Patronymic')
                        if family_name is not None and first_name is not None and patronymic is not None:
                            type_name_enc_gkn = self.encumbrance_classifier[type_obr_gkn.text] + ' ' + \
                                            family_name.text + ' ' + first_name.text + ' ' + patronymic.text
                        if type_name_enc_gkn not in list_arendatorov:
                            list_arendatorov.append(type_name_enc_gkn)
                    elif type_obr_gkn is not None:
                        list_arendatorov.append(self.encumbrance_classifier[type_obr_gkn.text])
        # Приводим к нормальному виду ФИО арендаторов, записанные большими буквами
        for i in list_arendatorov:
            s = re.search('"', i)
            lst = i.split(' ')
            if s is None:
                if len(lst) == 4:
                    new_list_arendatorov.append(i.title())
                elif len(lst) > 4:
                    lst[len(lst) - 1] = lst[len(lst) - 1].title()
                    lst[len(lst) - 2] = lst[len(lst) - 2].title()
                    lst[len(lst) - 3] = lst[len(lst) - 3].title()
                    new_list_arendatorov.append(' '.join(lst))
            else:
                new_list_arendatorov.append(i)
        if obrem != '' and new_list_arendatorov != []:
            return ', '.join(new_list_arendatorov) + '; ' + obrem
        elif obrem != '' and new_list_arendatorov == []:
            return obrem
        else:
            return ', '.join(new_list_arendatorov)

    @property
    def encumbrances_name_reg_numb_date_duration(self):
        """
        возвращает вид ограничения (обременения), его регистрационный номер, дату регистрации, срок действия
        :return: str
        """
        rental_periods = []
        if self._extract_object_right is not None:
            for right in self._extract_object_right.findall(self._dop + 'ExtractObject/' +
                                                            self._dop + 'ObjectRight/' +
                                                            self._dop + 'Right'):
                for childs in right:
                    if childs.tag == self._dop + 'Encumbrance':
                        rent = childs.find(self._dop + 'Duration')
                        if rent is not None:
                            start_rent = rent.find(self._dop + 'Started')
                            end_rent = rent.find(self._dop + 'Stopped')
                            if rent is not None:
                                term_r = rent.find(self._dop + 'Term')
                                if term_r is not None:
                                    rent_term = term_r.text
                                elif start_rent is not None and end_rent is not None:
                                    rent_term = "c " + start_rent.text + " по " + end_rent.text
                                else:
                                    rent_term = ""
                            doc = []
                            for child in childs.findall(self._dop + 'DocFound'):
                                content = child.find(self._dop + 'Content')
                                if content is not None:
                                    if content.text not in doc:
                                        doc.append(content.text)
                            if rent_term is not None and doc is not None:
                                if (", ".join(doc) + ", срок действия: " + rent_term) not in rental_periods:
                                    rental_periods.append(", ".join(doc) + ", срок действия: " + rent_term)
        if not rental_periods:
            encumbrances_gkn = self._realty.find(self._dop + 'Encumbrances')
            if encumbrances_gkn is not None:
                for encumbrance_gkn in encumbrances_gkn.findall(self._dop + 'Encumbrance'):
                    type_obr_gkn = encumbrance_gkn.find(self._dop + 'Type')
                    reg_number = encumbrance_gkn.find(self._dop + 'Registration/' + self._dop + 'RegNumber')
                    enc_cad_number = encumbrance_gkn.find(self._dop + 'CadastralNumberRestriction')
                    rn_rent_gkn = None
                    if reg_number is not None:
                        rn_rent_gkn = reg_number
                    elif enc_cad_number is not None:
                        rn_rent_gkn = enc_cad_number
                    rd_rent_gkn = encumbrance_gkn.find(self._dop + 'Registration/' + self._dop + 'RegDate')
                    if type_obr_gkn is not None and rn_rent_gkn is not None and rd_rent_gkn is not None:
                        name_numb_date = self.encumbrance_classifier[type_obr_gkn.text] + ' №' + rn_rent_gkn.text +\
                                         ' от ' + rd_rent_gkn.text
                        if name_numb_date not in rental_periods:
                            rental_periods.append(name_numb_date)
        return "; ".join(rental_periods)

    @property
    def extract_date(self):
        """
        возвращает дату выгрузки выписки из ЕГРН (день, в который была актуальной информация, содержащаяся  в выписке)
        :return: str
        """
        date = ''
        if self._extract_object_right is not None:
            foot_content = self._extract_object_right.find(self._dop + 'FootContent')
            extract_date = foot_content.find(self._dop + 'ExtractDate')
            date = extract_date.text
        return date

    @property
    def date_of_cadastral_reg(self):
        """
        возвращает дату постановки объекта недвижимости на кадастровый учет (дату присвоения кадастрового номера)
        :return: str
        """
        real_estate_object = self._real_estate_object
        date = ''
        if real_estate_object is not None:
            if real_estate_object.get('DateCreated', None):
                date_created = real_estate_object.get('DateCreated')
            elif real_estate_object.get('DateCreatedDoc', None):
                date_created = real_estate_object.get('DateCreatedDoc')
            inverted_date = re.sub('-', '.', date_created)
            date = ".".join(inverted_date.split(".")[::-1])
        return date

    @property
    def special_notes(self):
        """
        возвращает особые отметки об  объекта недвижимости в ЕГРН
        :return: str
        """
        real_estate_object = self._real_estate_object
        spec_notes = None
        if real_estate_object is not None:
            spec_notes = real_estate_object.find(self._dop + 'Notes')
        if spec_notes is not None:
            return spec_notes.text
        else:
            return ''

    @property
    def estate_objects(self):
        """
        возвращает список кадастровых номеров расположенных в пределах земельного участка зданий, сооружений, объектов
        незавершенного строительства
        :return: str
        """
        estate_objects_cad_nums = []
        real_estate_object = self._real_estate_object
        if real_estate_object is not None:
            flats = real_estate_object.find(self._dop + 'Flats')
            if flats is not None:
                for flat in flats.findall(self._dop + 'Flat'):
                    estate_objects_cad_nums.append(flat.get('CadastralNumber'))
            return ', '.join(estate_objects_cad_nums)
        else:
            return ''

    def _get_geometry_from_spatial_element(self, spatial_elements, dop_cad_num: str, result: dict):
        points_x = []
        points_y = []
        num_point = []
        pos_next = 0
        for entity_spatial in spatial_elements.findall(self._dop + 'EntitySpatial'):
            coordinates = []
            multipolygon = {}
            for spatial_element in entity_spatial.findall(self._spat + ':SpatialElement', self._namespaces):
                for spelement_unit in spatial_element.findall(self._spat + ':SpelementUnit', self._namespaces):
                    ordinate = spelement_unit.find(self._spat + ':Ordinate', self._namespaces)
                    coord_x = float(ordinate.get('X'))
                    coord_y = float(ordinate.get('Y'))
                    points_x.append(coord_x)
                    points_y.append(coord_y)
                    su_nmb = spelement_unit.get('SuNmb')
                    if su_nmb not in num_point:
                        num_point.append(su_nmb)
                    else:
                        position = int(pos_next)
                        pos_next = len(points_x) + 1
                        multipolygon.update({position: pos_next})
                        num_point.append(su_nmb)
            # Для полигональных шейп-файлов полигональные координаты должны быть упорядочены по часовой стрелке.
            # если какой-либо из полигонов имеет отверстия, то координаты многоугольника отверстия должны быть
            # упорядочены в направлении против часовой стрелки. В выписках из ЕГРН и для полигонов и для их отверстий
            # координаты могут идти как по часовой, так и против часовой стрелки. Для определения направления координат
            # точек используем формулу площади Гаусса, в правой системе координат положительный знак площади указывает
            # направление точек против часовой стрелки, отрицательный - направление точек по часовой стрелке
            for key in multipolygon:
                if key > 0:
                    poly = []
                    for item in range(key, multipolygon[key]):
                        poly.append([points_y[item - 1], points_x[item - 1]])
                    if gauss_area(poly) > 0:
                        coordinates.append(poly[::-1])
                    else:
                        coordinates.append(poly)
                else:
                    poly = []
                    for item in range(key + 1, multipolygon[key]):
                        poly.append([points_y[item - 1], points_x[item - 1]])
                    if gauss_area(poly) > 0:
                        coordinates.append(poly)
                    else:
                        coordinates.append(poly[::-1])
            if coordinates:
                result.update({dop_cad_num: coordinates})

    @property
    def geometry(self):
        """
        возвращает пространственные данные земельного участка (тип геометрии - полигон) в виде словаря, в котором ключ -
        кадастровый номер, значение по ключу - список координат границ полигона в формате, используемом в библиотеке
        pyshp
        :return: dict
        """
        result = {}
        composition_ez = self._real_estate_object
        contours = self._realty.find(self._dop + 'Contours')
        if composition_ez is not None:
            dop_cad_num = composition_ez.get("CadastralNumber")
            self._get_geometry_from_spatial_element(composition_ez, dop_cad_num, result)
        elif contours is not None:
            for contour in contours.findall(self._dop + 'Contour'):
                dop_cad_num = self.parent_cad_number + '(' + contour.get('NumberRecord') + ')'
                self._get_geometry_from_spatial_element(contour, dop_cad_num, result)
        else:
            self._get_geometry_from_spatial_element(self._realty, self.parent_cad_number, result)
        return result


class ObjectOfCapitalConstructionKVOKS(AbstractOCC):
    def __init__(self, xml_file_path, settings, root, dop):
        super().__init__(xml_file_path, settings, root, dop)
        self._realty = self._root.find(self._dop + 'Realty')
        self._extract_object_right = self._root.find(self._dop + 'ReestrExtract/' + self._dop + 'ExtractObjectRight')
        self._namespaces = {
            'smev': 'urn://x-artefacts-smev-gov-ru/supplementary/commons/1.0.1',
            'num': 'urn://x-artefacts-rosreestr-ru/commons/complex-types/numbers/1.0',
            'adrs': 'urn://x-artefacts-rosreestr-ru/commons/complex-types/address-output/4.0.1',
            'spa': 'urn://x-artefacts-rosreestr-ru/commons/complex-types/entity-spatial/5.0.1',
            'param': 'urn://x-artefacts-rosreestr-ru/commons/complex-types/parameters-oks/2.0.1',
            'cer': 'urn://x-artefacts-rosreestr-ru/commons/complex-types/certification-doc/1.0',
            'doc': 'urn://x-artefacts-rosreestr-ru/commons/complex-types/document-output/4.0.1',
            'flat': 'urn://x-artefacts-rosreestr-ru/commons/complex-types/assignation-flat/1.0.1',
            'ch': 'urn://x-artefacts-rosreestr-ru/commons/complex-types/cultural-heritage/2.0.1'
        }
        self._adr = 'adrs'
        self._spat = 'spa'


class ObjectOfCapitalConstructionKPOKS(AbstractOCC):
    def __init__(self, xml_file_path, settings, root, dop):
        super().__init__(xml_file_path, settings, root, dop)
        self._realty = self._root.find(self._dop + 'Realty')
        self._extract_object_right = self._root.find(self._dop + 'ReestrExtract/' + self._dop + 'ExtractObjectRight')
        self._namespaces = {
            'smev': 'urn://x-artefacts-smev-gov-ru/supplementary/commons/1.0.1',
            'num': 'urn://x-artefacts-rosreestr-ru/commons/complex-types/numbers/1.0',
            'adrs': 'urn://x-artefacts-rosreestr-ru/commons/complex-types/address-output/4.0.1',
            'spa': 'urn://x-artefacts-rosreestr-ru/commons/complex-types/entity-spatial/5.0.1',
            'param': 'urn://x-artefacts-rosreestr-ru/commons/complex-types/parameters-oks/2.0.1',
            'cer': 'urn://x-artefacts-rosreestr-ru/commons/complex-types/certification-doc/1.0',
            'doc': 'urn://x-artefacts-rosreestr-ru/commons/complex-types/document-output/4.0.1',
            'flat': 'urn://x-artefacts-rosreestr-ru/commons/complex-types/assignation-flat/1.0.1',
            'ch': 'urn://x-artefacts-rosreestr-ru/commons/complex-types/cultural-heritage/2.0.1'
        }
        self._adr = 'adrs'
        self._spat = 'spa'
