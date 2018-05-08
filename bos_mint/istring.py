# -*- coding: utf-8 -*-


class LanguageNotFoundException(BaseException):
    pass


class InternationalizedString(object):
    LANGUAGES = [
        ("display_name", "Display Name"),
        ("sen", "Short English"),
        ("ab", "Abkhazian"),
        ("aa", "Afar"),
        ("af", "Afrikaans"),
        ("ak", "Akan"),
        ("sq", "Albanian"),
        ("am", "Amharic"),
        ("ar", "Arabic"),
        ("an", "Aragonese"),
        ("hy", "Armenian"),
        ("as", "Assamese"),
        ("av", "Avaric"),
        ("ae", "Avestan"),
        ("ay", "Aymara"),
        ("az", "Azerbaijani"),
        ("bm", "Bambara"),
        ("ba", "Bashkir"),
        ("eu", "Basque"),
        ("be", "Belarusian"),
        ("bn", "Bengali (Bangla)"),
        ("bh", "Bihari"),
        ("bi", "Bislama"),
        ("bs", "Bosnian"),
        ("br", "Breton"),
        ("bg", "Bulgarian"),
        ("my", "Burmese"),
        ("ca", "Catalan"),
        ("ch", "Chamorro"),
        ("ce", "Chechen"),
        ("ny", "Chichewa, Chewa, Nyanja"),
        ("zh", "Chinese"),
        ("zh_Hans", "Chinese (Simplified)"),
        ("zh_Hant", "Chinese (Traditional)"),
        ("cv", "Chuvash"),
        ("kw", "Cornish"),
        ("co", "Corsican"),
        ("cr", "Cree"),
        ("hr", "Croatian"),
        ("cs", "Czech"),
        ("da", "Danish"),
        ("dv", "Divehi, Dhivehi, Maldivian"),
        ("nl", "Dutch"),
        ("dz", "Dzongkha"),
        ("en", "English"),
        ("eo", "Esperanto"),
        ("et", "Estonian"),
        ("ee", "Ewe"),
        ("fo", "Faroese"),
        ("fj", "Fijian"),
        ("fi", "Finnish"),
        ("fr", "French"),
        ("ff", "Fula, Fulah, Pulaar, Pular"),
        ("gl", "Galician"),
        ("gd", "Gaelic (Scottish)"),
        ("gv", "Gaelic (Manx)"),
        ("ka", "Georgian"),
        ("de", "German"),
        ("gr", "Greek"),
        ("kl", "Greenlandic"),
        ("gn", "Guarani"),
        ("gu", "Gujarati"),
        ("ht", "Haitian Creole"),
        ("ha", "Hausa"),
        ("he", "Hebrew"),
        ("hz", "Herero"),
        ("hi", "Hindi"),
        ("ho", "Hiri Motu"),
        ("hu", "Hungarian"),
        ("is", "Icelandic"),
        ("io", "Ido"),
        ("ig", "Igbo"),
        ("id", "Indonesian"),
        ("in", "Indonesian"),
        ("ia", "Interlingua"),
        ("ie", "Interlingue"),
        ("iu", "Inuktitut"),
        ("ik", "Inupiak"),
        ("ga", "Irish"),
        ("it", "Italian"),
        ("ja", "Japanese"),
        ("jv", "Javanese"),
        ("kl", "Kalaallisut, Greenlandic"),
        ("kn", "Kannada"),
        ("kr", "Kanuri"),
        ("ks", "Kashmiri"),
        ("kk", "Kazakh"),
        ("km", "Khmer"),
        ("ki", "Kikuyu"),
        ("rw", "Kinyarwanda (Rwanda)"),
        ("rn", "Kirundi"),
        ("ky", "Kyrgyz"),
        ("kv", "Komi"),
        ("kg", "Kongo"),
        ("ko", "Korean"),
        ("ku", "Kurdish"),
        ("kj", "Kwanyama"),
        ("lo", "Lao"),
        ("la", "Latin"),
        ("lv", "Latvian (Lettish)"),
        ("li", "Limburgish ( Limburger)"),
        ("ln", "Lingala"),
        ("lt", "Lithuanian"),
        ("lu", "Luga-Katanga"),
        ("lg", "Luganda, Ganda"),
        ("lb", "Luxembourgish"),
        ("gv", "Manx"),
        ("mk", "Macedonian"),
        ("mg", "Malagasy"),
        ("ms", "Malay"),
        ("ml", "Malayalam"),
        ("mt", "Maltese"),
        ("mi", "Maori"),
        ("mr", "Marathi"),
        ("mh", "Marshallese"),
        ("mo", "Moldavian"),
        ("mn", "Mongolian"),
        ("na", "Nauru"),
        ("nv", "Navajo"),
        ("ng", "Ndonga"),
        ("nd", "Northern Ndebele"),
        ("ne", "Nepali"),
        ("no", "Norwegian"),
        ("nb", "Norwegian bokm��l"),
        ("nn", "Norwegian nynorsk"),
        ("ii", "Nuosu"),
        ("oc", "Occitan"),
        ("oj", "Ojibwe"),
        ("cu", "Old Church Slavonic, Old Bulgarian"),
        ("or", "Oriya"),
        ("om", "Oromo (Afaan Oromo)"),
        ("os", "Ossetian"),
        ("pi", "P��li"),
        ("ps", "Pashto, Pushto"),
        ("fa", "Persian (Farsi)"),
        ("pl", "Polish"),
        ("pt", "Portuguese"),
        ("pa", "Punjabi (Eastern)"),
        ("qu", "Quechua"),
        ("rm", "Romansh"),
        ("ro", "Romanian"),
        ("ru", "Russian"),
        ("se", "Sami"),
        ("sm", "Samoan"),
        ("sg", "Sango"),
        ("sa", "Sanskrit"),
        ("sr", "Serbian"),
        ("sh", "Serbo-Croatian"),
        ("st", "Sesotho"),
        ("tn", "Setswana"),
        ("sn", "Shona"),
        ("ii", "Sichuan Yi"),
        ("sd", "Sindhi"),
        ("si", "Sinhalese"),
        ("ss", "Siswati"),
        ("sk", "Slovak"),
        ("sl", "Slovenian"),
        ("so", "Somali"),
        ("nr", "Southern Ndebele"),
        ("es", "Spanish"),
        ("su", "Sundanese"),
        ("sw", "Swahili (Kiswahili)"),
        ("ss", "Swati"),
        ("sv", "Swedish"),
        ("tl", "Tagalog"),
        ("ty", "Tahitian"),
        ("tg", "Tajik"),
        ("ta", "Tamil"),
        ("tt", "Tatar"),
        ("te", "Telugu"),
        ("th", "Thai"),
        ("bo", "Tibetan"),
        ("ti", "Tigrinya"),
        ("to", "Tonga"),
        ("ts", "Tsonga"),
        ("tr", "Turkish"),
        ("tk", "Turkmen"),
        ("tw", "Twi"),
        ("ug", "Uyghur"),
        ("uk", "Ukrainian"),
        ("ur", "Urdu"),
        ("uz", "Uzbek"),
        ("ve", "Venda"),
        ("vi", "Vietnamese"),
        ("vo", "Volap��k"),
        ("wa", "Wallon"),
        ("cy", "Welsh"),
        ("wo", "Wolof"),
        ("fy", "Western Frisian"),
        ("xh", "Xhosa"),
        ("yi", "Yiddish"),
        ("ji", "Yiddish"),
        ("yo", "Yoruba"),
        ("za", "Zhuang, Chuang"),
        ("zu", "Zulu"),
        ("unknown", "Unknown language"),
    ]
    UNKNOWN = "Unknown"

    def __init__(self, country, text):
        '''
        Constructor
        '''
        self.country = country
        self.text = text

        if self.country not in [
            x[0] for x in InternationalizedString.LANGUAGES
        ] and not country == self.UNKNOWN:
            raise LanguageNotFoundException

    def getForm(self):
        from bos_mint.forms import InternationalizedStringForm
        lng = InternationalizedStringForm()
        lng.country = self.country
        lng.text = self.text
        return lng

    @classmethod
    def listToDict(cls, listOfIStrings):
        return {x[0]: x[1] for x in listOfIStrings}

    @classmethod
    def getChoices(cls):
        return [
            (x[0], x[0] + " - " + x[1])
            for x in InternationalizedString.LANGUAGES
        ]

    @classmethod
    def parseToList(cls, fieldListOfInternationalizedString):
        from bos_mint.forms import TranslatedFieldForm
        from wtforms import FormField

        istrings = list()

        if (
            isinstance(
                fieldListOfInternationalizedString, FormField) and
            isinstance(
                fieldListOfInternationalizedString.form, TranslatedFieldForm
            )
        ):
            fieldListOfInternationalizedString = \
                fieldListOfInternationalizedString.form.translations

        for ffield in fieldListOfInternationalizedString.entries:
            istrings.append([ffield.data["country"], ffield.data["text"]])

        return istrings
