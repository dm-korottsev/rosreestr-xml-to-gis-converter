from abc import ABC
import re
import json
import xml.etree.ElementTree as ElT
from logic import get_dict_from_csv, gauss_area

__author__ = "Dmitry S. Korottsev"
__copyright__ = "Copyright 2020"
__credits__ = []
__license__ = "GPL v3"
__version__ = "1.4"
__maintainer__ = "Dmitry S. Korottsev"
__email__ = "dm-korottev@yandex.ru"
__status__ = "Development"


class AbstractParcel(ABC):
    def __init__(self, xml_file_path, settings, root, dop):
        self.xml_file_path = xml_file_path
        self._root = root
        self._dop = dop
        self._parcel = None
        self._extract_object_right = None
        self._namespaces = dict()
        self._adr = ''
        self._spat = ''
        self._settings = settings
        self.codes_of_rf_regions = get_dict_from_csv('region.csv')  # коды регионов РФ
        self.status_classifier = get_dict_from_csv('status.csv')  # коды статусов земельных участков
        self.land_category_classifier = get_dict_from_csv('land_category.csv')  # коды категорий земель
        self.permitted_use_classifier = get_dict_from_csv('utilization.csv')  # коды видов разрешённого использования
        self.rights_classifier = get_dict_from_csv('right.csv')  # коды видов прав
        self.encumbrance_classifier = get_dict_from_csv('encumbrance.csv')  # коды видов ограничений (обременений)

    @staticmethod
    def create_a_parcel_object(xml_file_path: str):
        """
        Определяет xml-схему выписки на земельный участок и возвращает экземпляр соответствующего ей класса.
        В случае, если xml-схема выписки из Росреестра неизвестна, возвращает None.
        """
        tree = ElT.parse(xml_file_path)
        root = tree.getroot()
        d1 = '{urn://x-artefacts-rosreestr-ru/outgoing/kvzu/7.0.1}'
        d2 = '{urn://x-artefacts-rosreestr-ru/outgoing/kpzu/6.0.1}'
        with open('settings.json', 'r') as f:
            sd = json.load(f)
        if root.find(d1 + 'Parcels/' + d1 + 'Parcel') is not None:
            return ParcelKVZU(xml_file_path, sd, root, d1)
        elif root.find(d2 + 'Parcel') is not None:
            return ParcelKPZU(xml_file_path, sd, root, d2)
        elif root.find('land_record') is not None:
            return ParcelEGRN(xml_file_path, sd, root, None)
        else:
            return None

    @property
    def parent_cad_number(self):
        """
        возвращает для обычного земельного участка - его кадастровый номер,
        для единого землепользования - кадастровый номер единого землепользования
        :return: str
        """
        cad_number = self._parcel.get('CadastralNumber')
        return cad_number

    @property
    def entry_parcels(self):
        """
        возвращает список кадастровых номеров земельных участков, входящих в состав единого землепользования
        :return: list
        """
        cadastral_numbers = []
        composition_ez = self._parcel.find(self._dop + 'CompositionEZ')
        if composition_ez is not None:
            for entry_parcel in composition_ez.findall(self._dop + 'EntryParcel'):
                cadastral_numbers.append(entry_parcel.get('CadastralNumber'))
        return cadastral_numbers

    @property
    def area(self):
        """
        возвращает площадь земельного участка в квадратных метрах
        :return: str
        """
        t1_area = self._parcel.find(self._dop + 'Area')
        t2_area = t1_area.find(self._dop + 'Area')
        parcel_area = t2_area.text
        return parcel_area

    @property
    def status(self):
        """
        возвращает статус земельного участка (например: учтённый, временный и т.д.)
        :return: str
        """
        st = self.status_classifier[self._parcel.get('State')]
        return st

    @property
    def address(self):
        """
        возвращает адрес земельного участка в человекочитаемом виде
        :return: str
        """
        t_address = None
        address_note = None
        location = self._parcel.find(self._dop + 'Location')
        if location is not None:
            t_address = location.find(self._dop + 'Address')
        if t_address is not None:
            address_note = t_address.find(self._adr + ':Note', self._namespaces)
        if address_note is not None:
            address = address_note.text        
            if address == ',':
                address = ''
        else:
            region = t_address.find(self._adr + ':Region', self._namespaces)
            district = t_address.find(self._adr + ':District', self._namespaces)
            locality = t_address.find(self._adr + ':Locality', self._namespaces)
            if region is not None and district is not None and locality is not None:
                address = self.codes_of_rf_regions[region.text] + ', ' + district.get('Name') + ' ' +\
                          district.get('Type') + ', ' + locality.get('Type') + ' ' + locality.get('Name')
            elif region is not None and district is not None:
                address = self.codes_of_rf_regions[region.text] + ', ' + district.get('Name') + ' ' +\
                          district.get('Type')
            elif region is not None:
                address = self.codes_of_rf_regions[region.text]
            else:
                address = ''
        return address

    @property
    def district_name(self):
        district_name = ''
        location = self._parcel.find(self._dop + 'Location')
        if location is not None:
            t_address = location.find(self._dop + 'Address')
            district = t_address.find(self._adr + ':District', self._namespaces)
            if district is not None:
                district_name = district.get('Name')
        return district_name

    @property
    def category(self):
        """
        возвращает категорию земель
        :return: str
        """
        t_category = self._parcel.find(self._dop + 'Category')
        if t_category is not None:
            category = self.land_category_classifier[t_category.text]
        else:
            category = self.land_category_classifier['003008000000']
        return category

    @property
    def permitted_use_by_doc(self):
        """
        возвращает вид разрешённого использования (по документу)
        :return: str
        """
        utilization = self._parcel.find(self._dop + 'Utilization')
        if utilization.get('ByDoc') is not None:
            utiliz_by_doc = utilization.get('ByDoc')
        else:
            utiliz_by_doc = '-'
        return utiliz_by_doc

    @property
    def cadastral_cost(self):
        """
        возвращает кадастровую стоимость земельного участка (в рублях)
        :return: str
        """
        cad_cost = self._parcel.find(self._dop + 'CadastralCost')
        if cad_cost is not None:
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
            rights_gkn = self._parcel.find(self._dop + 'Rights')
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
        # Для земель лесного или водного фонда собственником по умолчанию является РФ
        if (cell_owner == [] and self.category == 'Земли лесного фонда') or (cell_owner == [] and
                                                                             self.category == 'Земли водного фонда'):
            cell_owner.append('Собственность РФ')
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
            rights_gkn = self._parcel.find(self._dop + 'Rights')
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
            encumbrances_gkn = self._parcel.find(self._dop + 'Encumbrances')
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
            encumbrances_gkn = self._parcel.find(self._dop + 'Encumbrances')
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
        возвращает дату постановки земельного участка на кадастровый учет (дату присвоения кадастрового номера)
        :return: str
        """
        if self._parcel.get('DateCreated', None):
            date_created = self._parcel.get('DateCreated')
        elif self._parcel.get('DateCreatedDoc', None):
            date_created = self._parcel.get('DateCreatedDoc')
        inverted_date = re.sub('-', '.', date_created)
        date = ".".join(inverted_date.split(".")[::-1])
        return date

    @property
    def special_notes(self):
        """
        возвращает особые отметки о земельном участке в ЕГРН
        :return: str
        """
        spec_notes = self._parcel.find(self._dop + 'SpecialNote')
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
        inner_cadastral_numbers = self._parcel.find(self._dop + 'InnerCadastralNumbers')
        if inner_cadastral_numbers is not None:
            for cadastral_number in inner_cadastral_numbers.findall(self._dop + 'CadastralNumber'):
                estate_objects_cad_nums.append(cadastral_number.text)
        return ', '.join(estate_objects_cad_nums)

    def _get_geometry_from_spatial_element(self, spatial_elements, dop_cad_num: str, result: dict):
        points_x = []
        points_y = []
        num_point = []
        pos_next = 0
        for entity_spatial in spatial_elements.findall(self._dop + 'EntitySpatial'):
            coordinates = []
            multipolygon = {}
            for spatial_element in entity_spatial.findall(self._spat + ':SpatialElement',
                                                          self._namespaces):
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
        composition_ez = self._parcel.find(self._dop + 'CompositionEZ')
        contours = self._parcel.find(self._dop + 'Contours')
        if composition_ez is not None:
            for entry_parcel in composition_ez.findall(self._dop + 'EntryParcel'):
                dop_cad_num = entry_parcel.get('CadastralNumber')
                self._get_geometry_from_spatial_element(entry_parcel, dop_cad_num, result)
        elif contours is not None:
            for contour in contours.findall(self._dop + 'Contour'):
                dop_cad_num = self.parent_cad_number + '(' + contour.get('NumberRecord') + ')'
                self._get_geometry_from_spatial_element(contour, dop_cad_num, result)
        else:
            self._get_geometry_from_spatial_element(self._parcel, self.parent_cad_number, result)
        return result


class ParcelKVZU(AbstractParcel):
    def __init__(self, xml_file_path, settings, root, dop):
        super().__init__(xml_file_path, settings, root, dop)
        self._parcel = self._root.find(self._dop + 'Parcels/' + self._dop + 'Parcel')
        self._extract_object_right = self._root.find(self._dop + 'ReestrExtract/' + self._dop + 'ExtractObjectRight')
        self._namespaces = {'smev': 'urn://x-artefacts-smev-gov-ru/supplementary/commons/1.0.1',
                            'num': 'urn://x-artefacts-rosreestr-ru/commons/complex-types/numbers/1.0',
                            'adrs': 'urn://x-artefacts-rosreestr-ru/commons/complex-types/address-output/4.0.1',
                            'spa': 'urn://x-artefacts-rosreestr-ru/commons/complex-types/entity-spatial/5.0.1',
                            'cer': 'urn://x-artefacts-rosreestr-ru/commons/complex-types/certification-doc/1.0',
                            'doc': 'urn://x-artefacts-rosreestr-ru/commons/complex-types/document-output/4.0.1',
                            'nobj': 'urn://x-artefacts-rosreestr-ru/commons/complex-types/natural-objects-output/1.0.1'}
        self._adr = 'adrs'
        self._spat = 'spa'


class ParcelKPZU(AbstractParcel):
    def __init__(self, xml_file_path, settings, root, dop):
        super().__init__(xml_file_path, settings, root, dop)
        self._parcel = self._root.find(self._dop + 'Parcel')
        self._extract_object_right = self._root.find(self._dop + 'ReestrExtract/' + self._dop + 'ExtractObjectRight')
        self._namespaces = {'ns5': "urn://x-artefacts-smev-gov-ru/supplementary/commons/1.0.1",
                            'ns2': "urn://x-artefacts-rosreestr-ru/commons/complex-types/numbers/1.0",
                            'adrOut4': "urn://x-artefacts-rosreestr-ru/commons/complex-types/address-output/4.0.1",
                            'ns7': "urn://x-artefacts-rosreestr-ru/commons/complex-types/entity-spatial/5.0.1",
                            'ns8': "urn://x-artefacts-rosreestr-ru/commons/complex-types/certification-doc/1.0",
                            'ns6': "urn://x-artefacts-rosreestr-ru/commons/complex-types/document-output/4.0.1",
                            'ns4': "urn://x-artefacts-rosreestr-ru/commons/complex-types/natural-objects-output/1.0.1"}
        self._adr = 'adrOut4'
        self._spat = 'ns7'


class ParcelEGRN(AbstractParcel):
    def __init__(self, xml_file_path, settings, root, dop):
        super().__init__(xml_file_path, settings, root, dop)
        self._land_record = self._root.find('land_record')
        self._params = self._land_record.find('params')
        self._right_records = self._root.find('right_records')
        self._restrict_records = self._root.find('restrict_records')

    @property
    def parent_cad_number(self):
        """
        возвращает для обычного земельного участка - его кадастровый номер,
        для единого землепользования - кадастровый номер единого землепользования
        :return: str
        """
        p_object = self._land_record.find('object')
        common_data = p_object.find('common_data')
        cad_number = common_data.find('cad_number')
        return cad_number.text

    @property
    def entry_parcels(self):
        """
        возвращает список кадастровых номеров земельных участков, входящих в состав единого землепользования
        :return: list
        """
        cadastral_numbers = []
        cad_links = self._land_record.find('cad_links')
        if cad_links is not None:
            common_land = cad_links.find('common_land')
            if common_land is not None:
                common_land_parts = common_land.find('common_land_parts')
                included_cad_numbers = common_land_parts.find('included_cad_numbers')
                for included_cad_number in included_cad_numbers.findall('included_cad_number'):
                    cad_number = included_cad_number.find('cad_number')
                    cadastral_numbers.append(cad_number.text)
        # если КН ЗУ, входящих в единое землепользование, указаны только в особых отметках, берём их оттуда
        if not cadastral_numbers:
            sp_notes = self.special_notes
            text = r"Кадастровые номера обособленных \(условных\) участков, входящих в единое землепользование:"
            if re.search(text, sp_notes):
                lst_cad_n = re.findall(r"\d+:\d+:\d+:\d+", sp_notes)
                for entry_cad_n in lst_cad_n:
                    cadastral_numbers.append(entry_cad_n)
        return cadastral_numbers

    @property
    def area(self):
        """
        возвращает площадь земельного участка в квадратных метрах
        :return: str
        """
        t_area = self._params.find('area')
        value = t_area.find('value')
        return value.text

    @property
    def address(self):
        """
        возвращает адрес земельного участка в человекочитаемом виде
        :return: str
        """
        address = ''
        address_location = self._land_record.find('address_location')
        if address_location is not None:
            address_t = address_location.find('address')
            readable_address = address_t.find('readable_address')
            if readable_address is not None:
                address = readable_address.text
        return address

    @property
    def status(self):
        """
        возвращает статус земельного участка (например: учтённый, временный и т.д.)
        :return: str
        """
        st = self._root.find('status')
        return st.text

    @property
    def category(self):
        """
        возвращает категорию земель
        :return: str
        """
        t_category = self._params.find('category')
        if t_category is not None:
            type = t_category.find('type')
            code = type.find('code')
            return self.land_category_classifier[code.text]
        else:
            return ''

    @property
    def permitted_use_by_doc(self):
        """
        возвращает вид разрешённого использования (по документу)
        :return: str
        """
        permitted_use = self._params.find('permitted_use')
        if permitted_use is not None:
            permitted_use_established = permitted_use.find('permitted_use_established')
            by_document = permitted_use_established.find('by_document')
            return by_document.text
        else:
            return ''

    @property
    def cadastral_cost(self):
        """
        возвращает кадастровую стоимость земельного участка (в рублях)
        :return: str
        """
        cad_cost = self._land_record.find('cost')
        if cad_cost is not None:
            value = cad_cost.find('value')
            cad_cost_value = value.text
        else:
            cad_cost_value = ''
        return cad_cost_value

    @property
    def owner(self):
        """
        возвращает список правообладателей (вид права и лицо, владеющее этим правом)
        :return: str
        """
        r_type = ''
        r_type_list = []
        lst_holders = []
        shared_ownership_list = []
        share_list = []
        denominators = set()
        cells_owners = []
        if self._right_records is not None:
            for record in self._right_records.findall('right_record'):
                right_data = record.find('right_data')
                right_type = right_data.find('right_type')
                value = right_type.find('value')
                if value is not None:
                    r_type = value.text
                    r_type_list.append(value.text)
                if r_type == 'Общая долевая собственность':
                    shares = right_data.find('shares')
                    share = shares.find('share')
                    numerator = share.find('numerator')
                    denominator = share.find('denominator')
                    if numerator is not None and denominator is not None:
                        share_list.append(numerator.text + '/' + denominator.text)
                        denominators.add(int(denominator.text))
                right_holders = record.find('right_holders')
                for right_holder in right_holders.findall('right_holder'):
                    if r_type == 'Общая долевая собственность':
                        for childs in right_holder:
                            if childs.tag == 'individual':
                                surname = childs.find('surname')
                                name = childs.find('name')
                                patronymic = childs.find('patronymic')
                                if surname is not None and name is not None and patronymic is not None:
                                    shared_ownership_list.append(surname.text + ' ' + name.text + ' ' + patronymic.text)
                    else:
                        for childs in right_holder:
                            if childs.tag == 'public_formation':  # Публично-правовое образование
                                public_formation_type = childs.find('public_formation_type')
                                for child in public_formation_type:
                                    if child.tag == 'russia' or child.tag == 'subject_of_rf':
                                        name = child.find('name')
                                        value = name.find('value')
                                        if value is not None:
                                            lst_holders.append(value.text)
                            elif childs.tag == 'individual':  # Физическое лицо
                                surname = childs.find('surname')
                                name = childs.find('name')
                                patronymic = childs.find('patronymic')
                                if surname is not None and name is not None and patronymic is not None:
                                    lst_holders.append(surname.text + ' ' + name.text + ' ' + patronymic.text)
                            elif childs.tag == 'legal_entity':  # Юридическое лицо, орган власти
                                entity = childs.find('entity')
                                resident = entity.find('resident')
                                name = resident.find('name')
                                inn = resident.find('inn')
                                if name is not None and inn is not None:
                                    lst_holders.append(name.text + " ИНН: " + inn.text)
                                elif name is not None:
                                    lst_holders.append(name.text)
                            elif childs.tag == 'another':  # Иной субъект права
                                pass
        if len(r_type_list) == len(lst_holders):
            for i in range(len(r_type_list)):
                cells_owners.append(r_type_list[i] + ' ' + lst_holders[i])
        else:
            cells_owners.append(r_type + ' ' + ', '.join(lst_holders))
        if r_type != '' and lst_holders != []:
            return ', '.join(cells_owners)
        elif r_type != '' and shared_ownership_list != []:
            if r_type == 'Общая долевая собственность':
                if len(shared_ownership_list) > 2:
                    return r_type + '(' + str(max(denominators)) + ' долей; ' + str(len(shared_ownership_list)) + \
                           ' правообладателей)'
                elif len(shared_ownership_list) == 2:
                    return r_type + ': ' + share_list[0] + ' ' + shared_ownership_list[0] + ', ' + share_list[1] + \
                           ' ' + shared_ownership_list[1]
                elif len(shared_ownership_list) == 1:
                    return r_type + ': ' + share_list[0] + ' ' + shared_ownership_list[0]
        elif r_type != '':
            return r_type
        else:
            return ''

    @property
    def own_name_reg_numb_date(self):
        """
        возвращает вид права, номер регистрации и дату регистрации права на объект недвижимости
        :return: str
        """
        name_numb_date = []
        name = ''
        numb = ''
        date = ''
        if self._right_records is not None:
            for record in self._right_records.findall('right_record'):
                right_data = record.find('right_data')
                right_type = right_data.find('right_type')
                value = right_type.find('value')
                if value is not None:
                    name = value.text
                right_number = right_data.find('right_number')
                if right_number is not None:
                    numb = right_number.text
                record_info = record.find('record_info')
                registration_date = record_info.find('registration_date')
                if registration_date is not None:
                    date = registration_date.text
                if name != '' or numb != '' or date != '':
                    name_numb_date.append(name + ' №' + numb + ' от ' + date)
        if not name_numb_date:
            return '-'
        else:
            return '; '.join(name_numb_date)

    @property
    def encumbrances(self):
        """
        возвращает список ограничений (обременений) прав и лиц, в пользу которых они установлены
        :return: str
        """
        list_of_encumbrances = []
        subjects_or_right_holders = []
        encumbrance_type = ''
        if self._restrict_records is not None:
            for restrict_record in self._restrict_records.findall('restrict_record'):
                restrictions_encumbrances_data = restrict_record.find('restrictions_encumbrances_data')
                restriction_encumbrance_type = restrictions_encumbrances_data.find('restriction_encumbrance_type')
                value = restriction_encumbrance_type.find('value')
                if value is not None:
                    encumbrance_type = value.text
                restrict_parties = restrict_record.find('restrict_parties')
                right_holders = restrict_record.find('right_holders')
                if restrict_parties is not None:
                    restricted_rights_parties = restrict_parties.find('restricted_rights_parties')
                    for restricted_rights_party in restricted_rights_parties.findall('restricted_rights_party'):
                        subject = restricted_rights_party.find('subject')
                        subjects_or_right_holders.append(subject)
                elif right_holders is not None:
                    for right_holder in right_holders.findall('right_holder'):
                        subjects_or_right_holders.append(right_holder)
                for subject_or_right_holder in subjects_or_right_holders:
                    for childs in subject_or_right_holder:
                        if childs.tag == 'public_formation':
                            public_formation_type = childs.find('public_formation_type')
                            for pf_type in public_formation_type:
                                if pf_type.tag == 'foreign_public' or pf_type.tag == 'subject_of_rf':
                                    name = pf_type.find('name')
                                    value = name.find('value')
                                    if value is not None:
                                        list_of_encumbrances.append(encumbrance_type + ' ' + value.text)
                                elif pf_type.tag == 'union_state' or pf_type.tag == 'municipality':
                                    name = pf_type.find('name')
                                    if name is not None:
                                        list_of_encumbrances.append(encumbrance_type + ' ' + name.text)
                                elif pf_type.tag == 'russia':  # Российская Федерация
                                    list_of_encumbrances.append(encumbrance_type + ' РФ')
                        elif childs.tag == 'individual':
                            surname = childs.find('surname')
                            name = childs.find('name')
                            patronymic = childs.find('patronymic')
                            if surname is not None and name is not None and patronymic is not None:
                                list_of_encumbrances.append(encumbrance_type + ' ' + surname.text + ' ' + name.text +
                                                            ' ' + patronymic.text)
                        elif childs.tag == 'legal_entity':
                            entity = childs.find('entity')
                            for entity_out in entity:
                                if entity_out.tag == 'resident' or entity_out.tag == 'not_resident':  # юр. лицо
                                    name = entity_out.find('name')
                                    inn = entity_out.find('inn')
                                    if name is not None and inn is not None:
                                        list_of_encumbrances.append(encumbrance_type + ' ' + name.text + " ИНН: " +
                                                                    inn.text)
                                    elif name is not None:
                                        list_of_encumbrances.append(encumbrance_type + ' ' + name.text)
                                elif entity_out.tag == 'govement_entity':  # Орган государственной власти, орган МСУ
                                    full_name = entity_out.find('full_name')
                                    if full_name is not None:
                                        list_of_encumbrances.append(encumbrance_type + ' ' + full_name.text)
                        elif childs.tag == 'another':
                            another_type = childs.find('another_type')
                            for another in another_type:
                                if another.tag == 'investment_unit_owner':  # Владельцы инвестиционных паев
                                    investment_unit_name = another.find('investment_unit_name')
                                    if investment_unit_name is not None:
                                        list_of_encumbrances.append(encumbrance_type + ' ' + investment_unit_name.text)
                                elif another.tag == 'certificates_holders':  # Владельцы ипотечных сертификатов участия
                                    certificate_name = another.find('certificate_name')
                                    if certificate_name is not None:
                                        list_of_encumbrances.append(encumbrance_type + ' ' + certificate_name.text)
                                elif another.tag == 'bonds_holders':  # Владельцы облигаций
                                    bonds_number = another.find('bonds_number')
                                    if bonds_number is not None:
                                        list_of_encumbrances.append(encumbrance_type + ' ' + bonds_number.text)
                                elif another.tag == 'partnership':  # Инвестиционное товарищество
                                    partnership_participants = another.find('partnership_participants')
                                    for partnership_participant in partnership_participants.findall(
                                            'partnership_participant'):
                                        legal_entity = partnership_participant.find('legal_entity')
                                        entity = legal_entity.find('entity')
                                        for entity_ul in entity:
                                            if entity_ul.tag == 'resident' or entity_ul.tag == 'not_resident':
                                                name = entity_ul.find('name')
                                                if name is not None:
                                                    list_of_encumbrances.append(encumbrance_type + ' ' + name.text)
                                elif another.tag == 'aparthouse_owners':  # Собств. помещений в многоквартирном доме
                                    aparthouse_owners_name = another.find('aparthouse_owners_name')
                                    if aparthouse_owners_name is not None:
                                        list_of_encumbrances.append(encumbrance_type + ' ' +
                                                                    aparthouse_owners_name.text)
                                elif another.tag == 'equity_participants_info':  # Участники долевого строительства
                                    equity_participants = another.find('equity_participants')
                                    if equity_participants is not None:
                                        list_of_encumbrances.append(encumbrance_type + ' ' + equity_participants.text)
                                # Участники долевого строительства по договорам участия в долевом строительстве,
                                # которым не переданы объекты долевого строительства
                                elif another.tag == 'not_equity_participants_info':
                                    not_equity_participants = another.find('not_equity_participants')
                                    if not_equity_participants is not None:
                                        list_of_encumbrances.append(encumbrance_type + ' ' +
                                                                    not_equity_participants.text)
                                elif another.tag == 'other':
                                    name = another.find('name')
                                    if name is not None:
                                        list_of_encumbrances.append(encumbrance_type + ' ' + name.text)
                        elif childs.tag == 'public_servitude':
                            public = childs.find('public')
                            if public is not None:
                                list_of_encumbrances.append(public.text)
                        elif childs.tag == 'undefined':
                            undefined = childs.find('undefined')
                            if undefined is not None:
                                list_of_encumbrances.append(undefined.text)
        list_of_encumbrances = set(list_of_encumbrances)
        return ', '.join(list_of_encumbrances)

    @property
    def encumbrances_name_reg_numb_date_duration(self):
        """
        возвращает вид ограничения (обременения), его регистрационный номер, дату регистрации, срок действия
        :return: str
        """
        name_numb_date_dur = []
        if self._restrict_records is not None:
            for restrict_record in self._restrict_records.findall('restrict_record'):
                duration = None
                name = None
                number = None
                date = None
                restrictions_encumbrances_data = restrict_record.find('restrictions_encumbrances_data')
                restriction_encumbrance_type = restrictions_encumbrances_data.find('restriction_encumbrance_type')
                record_info = restrict_record.find('record_info')
                period = restrictions_encumbrances_data.find('period')
                if period is not None:
                    period_info = period.find('period_info')
                    period_ddu = period.find('period_ddu')
                    if period_info is not None:
                        start_date = period_info.find('start_date')
                        end_date = period_info.find('end_date')
                        deal_validity_time = period_info.find('deal_validity_time')
                        if start_date is not None and end_date is not None:
                            duration = 'срок действия: с ' + start_date.text + ' по ' + end_date.text
                        elif start_date is not None and deal_validity_time is not None:
                            duration = 'срок действия: с ' + start_date.text + ' на ' + deal_validity_time.text
                    if period_ddu is not None:
                        first_ddu_date = period_ddu.find('first_ddu_date')
                        transfer_deadline = period_ddu.find('transfer_deadline')
                        if first_ddu_date is not None and transfer_deadline is not None:
                            duration = 'дата регистрации первого ДДУ ' + first_ddu_date.text + \
                                       ', срок передачи застройщиком объекта ' + transfer_deadline.text
                encumbrance_name = restriction_encumbrance_type.find('value')
                if encumbrance_name is not None:
                    name = encumbrance_name.text
                encumbrance_number = restrictions_encumbrances_data.find('restriction_encumbrance_number')
                if encumbrance_number is not None:
                    number = encumbrance_number.text
                registration_date = record_info.find('registration_date')
                if registration_date is not None:
                    date = registration_date.text[:10]
                if (name and number and date and duration) is not None:
                    record = name + ' №' + number + ' от ' + date + ', ' + duration
                    name_numb_date_dur.append(record)
        if name_numb_date_dur:
            return ', '.join(name_numb_date_dur)
        else:
            return '-'

    @property
    def date_of_cadastral_reg(self):
        """
        возвращает дату постановки земельного участка на кадастровый учет
        :return: str
        """
        record_info = self._land_record.find('record_info')
        registration_date = record_info.find('registration_date')
        inverted_date = re.sub('-', '.', registration_date.text[:10])
        date = ".".join(inverted_date.split(".")[::-1])
        return date

    @property
    def extract_date(self):
        """
        возвращает дату выгрузки выписки из ЕГРН (день, в который была актуальной информация, содержащаяся  в выписке)
        :return: str
        """
        details_statement = self._root.find('details_statement')
        group_top_requisites = details_statement.find('group_top_requisites')
        date_formation = group_top_requisites.find('date_formation')
        inverted_date = re.sub('-', '.', date_formation.text[:10])
        date = ".".join(inverted_date.split(".")[::-1])
        return date

    @property
    def special_notes(self):
        """
        возвращает особые отметки о земельном участке в ЕГРН
        :return: str
        """
        spec_notes = self._land_record.find('special_notes')
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
        cad_numbers = ''
        cad_links = self._land_record.find('cad_links')
        if cad_links is not None:
            included_objects = cad_links.find('included_objects')
            if included_objects is not None:
                included_object = included_objects.find('included_object')
                if included_object is not None:
                    cad_number_el = included_object.find('cad_number')
                    if cad_number_el is not None:
                        cad_numbers = cad_number_el.text
        return cad_numbers

    def _get_geometry_from_spatial_element(self, contour, dop_cad_num: str, result: dict):
        """
        извлекает список координат границ полигона в формате, используемом в библиотеке pyshp и записывает их в словарь
        (ключ - кадастровый номер контура, значение - координаты контура)
        :param dop_cad_num: str
        :param result: dict
        """
        points_x = []
        points_y = []
        num_point = []
        multipolygon = {}
        pos_next = 0
        coordinates = []
        for entity_spatial in contour.findall('entity_spatial'):
            spatial_elements = entity_spatial.find('spatials_elements')
            for spatial_element in spatial_elements.findall('spatial_element'):
                ordinates = spatial_element.find('ordinates')
                for ordinate in ordinates.findall('ordinate'):
                    coord_x = ordinate.find('x')
                    coord_y = ordinate.find('_y')
                    if coord_y is None:
                        coord_y = ordinate.find('y')
                    points_x.append(float(coord_x.text))
                    points_y.append(float(coord_y.text))
                    if coord_x.text + coord_y.text not in num_point:
                        num_point.append(coord_x.text + coord_y.text)
                    else:
                        position = int(pos_next)
                        pos_next = len(points_x) + 1
                        multipolygon.update({position: pos_next})
                        num_point.append(coord_x.text + coord_y.text)
        if points_x != [] and points_y != []:
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
        contours_location = self._land_record.find('contours_location')
        if contours_location is not None:
            contours = contours_location.find('contours')
            if contours is not None:
                for contour in contours.findall('contour'):
                    cad_number = contour.find('cad_number')
                    number_pp = contour.find('number_pp')
                    if cad_number is not None:
                        dop_cad_num = cad_number.text
                    elif number_pp is not None:
                        dop_cad_num = number_pp.text
                    else:
                        dop_cad_num = self.parent_cad_number
                    self._get_geometry_from_spatial_element(contour, dop_cad_num, result)
        return result
