import csv
import re

# --- Built-in Dictionary for Segmentation ---
def get_khmer_dictionary():
    """
    Return the small built-in dictionary (213 unique entries in version 0.3.8).
    Coverage is limited; this is not a comprehensive Khmer lexicon.
    """
    return {
        'ស្ថិតនៅ', 'ក្នុង', 'ខេត្ត', 'សៀមរាប', 'ប្រទេស', 'កម្ពុជា', 'សាលារៀន', 'សួស្តី',
        'ខ្ញុំ', 'ស្រឡាញ់', 'ភាសាខ្មែរ', 'នេះ', 'គឺ', 'ជា', 'ស្ថិត', 'នៅ', 'វត្ត', 'បុរាណ',
        'មាន', 'ព្រះវិហារ', 'ធំ', 'បំផុត', 'ពេល', 'សម្រាក', 'ព្រឹក', 'មនុស្ស', 'ច្រើន', 'កូន',
        'សិស្ស', 'គ្រូ', 'បង្រៀន', 'សៀវភៅ', 'ប៊ិក', 'ខ្មៅដៃ', 'សាលា', 'រៀន', 'ទៅ', 'មក',
        'ញ៉ាំ', 'បាយ', 'ទឹក', 'ដោះគោ', 'ឆ្ងាញ់', 'ផ្ទះ', 'ឡាន', 'ម៉ូតូ', 'កង់', 'ដើរ', 'រត់',
        'លេង', 'ទាត់', 'បាល់', 'មិត្តភ័ក្តិ', 'ឪពុក', 'ម្តាយ', 'បង', 'ប្អូន', 'ប្រុស', 'ស្រី',
        'លោកគ្រូ', 'អ្នកគ្រូ', 'មន្ទីរពេទ្យ', 'ឈឺ', 'ពេទ្យ', 'ថ្នាំ', 'ព្យាបាល', 'ជាសះស្បើយ',
        'ទីផ្សារ', 'ទិញ', 'លក់', 'អីវ៉ាន់', 'បន្លែ', 'ផ្លែឈើ', 'សាច់', 'ត្រី', 'លុយ', 'កាក់',
        'កុំព្យូទ័រ', 'ទូរស័ព្ទ', 'កម្មវិធី', 'អ៊ីនធឺណិត', 'គេហទំព័រ', 'សរសេរ', 'អាន', 'និយាយ',
        'ស្តាប់', 'មើល', 'ទូរទស្សន៍', 'កុន', 'ចម្រៀង', 'ពិរោះ', 'ស្អាត', 'ល្អ', 'អាក្រក់',
        'ខ្ពស់', 'ទាប', 'វែង', 'ខ្លី', 'ធំ', 'តូច', 'ថ្មី', 'ចាស់', 'ក្តៅ', 'ត្រជាក់', 'ថ្ងៃ',
        'ខែ', 'ឆ្នាំ', 'ម៉ោង', 'នាទី', 'វិនាទី', 'ម្សិលមិញ', 'ថ្ងៃនេះ', 'ស្អែក', 'ព្រះអាទិត្យ',
        'ព្រះចន្ទ', 'ផ្កាយ', 'មេឃ', 'ដី', 'ភ្នំ', 'សមុទ្រ', 'ទន្លេ', 'បឹង', 'ព្រៃ', 'ឈើ', 'ផ្កា',
        'ក្រហម', 'ខៀវ', 'បៃតង', 'លឿង', 'ស', 'ខ្មៅ', 'ពណ៌', 'សំលៀកបំពាក់', 'អាវ', 'ខោ',
        'ស្បែកជើង', 'មួក', 'វ៉ែនតា', 'ឆ្កែ', 'ឆ្មា', 'មាន់', 'ទា', 'គោ', 'ជ្រូក', 'ដំរី',
        'ខ្លា', 'តោ', 'ស្វា', 'ពស់', 'ត្រី', 'សត្វ', 'ធ្វើការ', 'ក្រុមហ៊ុន', 'បុគ្គលិក',
        'ចៅហ្វាយ', 'លិខិត', 'របាយការណ៍', 'ប្រជុំ', 'សំខាន់', 'គម្រោង', 'ជោគជ័យ', 'បរាជ័យ',
        'ព្យាយាម', 'ឧស្សាហ៍', 'ខ្ជិល', 'ពូកែ', 'ខ្សោយ', 'ចំណេះដឹង', 'វិទ្យាសាស្ត្រ',
        'គណិតវិទ្យា', 'ប្រវត្តិសាស្ត្រ', 'ភូមិសាស្ត្រ', 'សិល្បៈ', 'តន្ត្រី', 'កីឡា', 'សុខភាព',
        'អាហារ', 'ភេសជ្ជៈ', 'ដំណេក', 'ភ្ញាក់', 'ដើរលេង', 'ដំណើរកម្សាន្ត', 'យន្តហោះ',
        'កប៉ាល់', 'រថភ្លើង', 'ផ្លូវ', 'ស្ពាន', 'អគារ', 'ភូមិ', 'ឃុំ', 'ស្រុក', 'ខេត្ត', 'រាជធានី',
        'ពិភពលោក', 'គ្រួសារ', 'សង្គម', 'រដ្ឋាភិបាល', 'នយោបាយ', 'សេដ្ឋកិច្ច', 'វប្បធម៌',
        'ប្រពៃណី', 'ជំនឿ', 'សាសនា', 'ស្នេហា', 'មិត្តភាព', 'ក្តីសង្ឃឹម', 'ក្តីសុខ', 'ទុក្ខ',
        'សប្បាយ', 'រីករាយ', 'កើតទុក្ខ', 'ខឹង', 'ខ្លាច', 'ភ្ញាក់ផ្អើល', 'ស្រស់ស្អាត', 'អស្ចារ្យ'
    }

# --- Custom Segmentation Logic (Replaces external libraries) ---
def longest_match_segmenter(text, dictionary):
    """
    A simple dictionary-based word segmenter using the longest match principle.
    """
    words = []
    current_pos = 0
    # Clean up the text by removing zero-width spaces that can appear
    clean_text = text.replace('\u200b', '').replace('.', ' . ').replace('។', ' ។ ')
    text_len = len(clean_text)
    max_word_length = max((len(word) for word in dictionary), default=0)

    while current_pos < text_len:
        longest_word = ''
        for i in range(min(text_len, current_pos + max_word_length), current_pos, -1):
            substring = clean_text[current_pos:i]
            if substring in dictionary:
                if len(substring) > len(longest_word):
                    longest_word = substring
                    break

        if not longest_word:
            # If no word is found, handle potential mix of Khmer and non-Khmer chars
            match = re.match(r'([\u1780-\u17FF]+|\s+|[a-zA-Z0-9]+|.)', clean_text[current_pos:])
            if match:
                longest_word = match.group(0)
            else:
                longest_word = clean_text[current_pos]

        if longest_word.strip():
            words.append(longest_word.strip())
        current_pos += len(longest_word)
    return words

def syllable_segmenter(text):
    """
    A basic rule-based syllable segmenter for Khmer.
    This is a simplified implementation.
    """
    syllable_pattern = r'([\u1780-\u17A2][\u17B6-\u17D3]*)'
    return [s for s in re.split(syllable_pattern, text) if s]

# --- Main Library Functions ---

def get_default_stop_words():
    """
    Returns a built-in set of Khmer stop words for automatic use.
    """
    stop_words_list = [
        'បន្ថែម', 'ខណៈនោះ', 'ខាងក្រោម', 'គ្រប់គ្រាន់', 'ដោយសារតែ', 'នៅពេលនោះ', 'ប្រទះឃើញ', 'ម្យ៉ាងទៀត',
        'យ៉ាងខាប់', 'លើក', 'ប្រាំ', 'វា', 'កម្រិត', 'កាន់', 'ការ', 'ការបើ', 'ការផ្លាស់ប្ដូរ',
        'ការរៀបចំ', 'កាលណា', 'កាលនោះ', 'ក្តី', 'ក្នុង', 'ក្នុងនេះ', 'ក្រាស់', 'ក្រោម', 'ក្រោយ',
        'ក្រោយមក', 'ក្លាយ', 'ក្លាយជា', 'កំពុង', 'កំពូល', 'កំឡុងពេល', 'ក៏', 'ក៏ដោយ', 'ក៏បាន',
        'ខាង', 'ខាងក្នុង', 'ខាងក្រោយ', 'ខាងក្រៅ', 'ខាងមុខ', 'ខាងលើ', 'ខុស', 'ខ្ងុំ', 'ខ្លួន',
        'ខ្លួនឯង', 'ខ្លះ', 'គាត់', 'គាំទ្រ', 'គឺ', 'គឺជា', 'គួរតែ', 'គួរសម', 'គេ', 'គ្នា',
        'គ្មាន', 'គ្មានមួយ', 'គ្រប់', 'គ្រា', 'គ្រាមួយ', 'ចង់', 'ចន្លោះ', 'ចាកពី', 'ចុង',
        'ចុងក្រោយ', 'ចេញ', 'ចេញពី', 'ចៃដន្យ', 'ច្រើន', 'ច្រើនជាងគេ', 'ចំណែក', 'ចំណោម',
        'ចំនួន', 'ចំនួនច្រើន', 'ចំពោះ', 'ចំហៀង', 'ឆ្ងាយ', 'ឆ្ងាយជាង', 'ឆ្ពោះទៅ', 'ជាដរាប',
        'ជានិច្ចកាល', 'ជាមុន', 'ជាមួយគ្នា', 'ជាស្រេច', 'ជិត', 'ជុំវិញ', 'ជួនកាល', 'ជួយ',
        'ជំរាល', 'ឈម', 'ញឹក', 'ញឹកញាប់', 'ញែក', 'ដកចេញ', 'ដង', 'ដដែល', 'ដល់', 'ដល់ម្ល៉េះ',
        'ដូចគ្នា', 'ដូចជា', 'ដូចនេះ', 'ដូចនេះហើយ', 'ដូចនោះ', 'ដូចម្ដេច', 'ដូច្នេះ',
        'ដូច្នេះហើយ', 'ដូច្នោះទេ', 'ដើម្បី', 'ដើម្បីនឹង', 'ដែរ', 'ដែល', 'ដែលក្រោយបំផុត',
        'ដែលក្លាយ', 'ដែលជា', 'ដែលជួយ', 'ដែលនឹង', 'ដែលអាច', 'ដោយ', 'ដោយខ្លួនឯង',
        'ដោយទីពីរ', 'ដោយភាគច្រើន', 'ដោយមិនដឹងជាយ៉ាងម៉េច', 'ដោយមិនដឹងជារឿងអ្វី',
        'ដោយមិនដឹងម៉េចទេ', 'ដោយហេតុថា', 'ដោយហេតុនោះ', 'ដំបូង', 'ដ៏ទៃ', 'ណា', 'ណាមួយ',
        'ណាស់', 'តាម', 'តាមចន្លោះ', 'តាំង', 'តាំងពី', 'តាំងពីនោះ', 'តើ', 'តែ', 'តែមួយ',
        'តោងតែ', 'ត្រង់នោះហើយ', 'ត្រឹម', 'ត្រឹមតែ', 'ត្រូវ', 'ត្រូវបាន', 'ថា', 'ថែមទៀត',
        'ថ្មី', 'ថ្វីបើ', 'ទទឹង', 'ទទួល', 'ទទេ', 'ទល់នឹង', 'ទាន់', 'ទាប', 'ទាល់តែ',
        'ទាស់', 'ទាំង', 'ទាំងនេះ', 'ទាំងពីរ', 'ទាំងមូល', 'ទាំងឡាយ', 'ទាំងអស់', 'ទី',
        'ទីកន្លែង', 'ទីណា', 'ទីនេះ', 'ទីនោះ', 'ទីពីរ', 'ទុក', 'ទុកបាន', 'ទូទាំង', 'ទៀត',
        'ទេ', 'ទោះបី', 'ទោះបីជា', 'ទៅ', 'ទៅដល់', 'ទៅផុត', 'ទៅលើ', 'ទំនង', 'ធម្មតា',
        'ធ្លាក់ចុះ', 'ធ្វើ', 'ធ្វើបាន', 'ធ្វើអោយបានចំរើន', 'នរណា', 'នាង', 'នាយ', 'និង',
        'និមួយ', 'និយម', 'នីមួយ', 'នឹង', 'នូវ', 'នេះ', 'នេះទៅទៀត', 'នៃ', 'នោះ', 'នោះទេ',
        'នោះមក', 'នោះឯង', 'នៅ', 'នៅក្នុង', 'នៅគ្រា', 'នៅជិតៗ', 'នៅតែ', 'នៅទី', 'នៅពេល',
        'នៅមុខ', 'នៅម្ដុំនេះ', 'នៅលើ', 'ន័យនេះ', 'បង្អស់', 'បន្ដិច', 'បន្ថែម', 'បន្ទាប់',
        'បន្ទាប់ពី', 'បន្ទាប់ពីនេះ', 'ប៉ុនគ្នា', 'ប៉ុន្ដែ', 'ប៉ុន្មាន', 'បានជា', 'បានដែរ',
        'បី', 'បីនេះ', 'បួន', 'បើ', 'បើមិនមែន', 'បែបនេះ', 'ប្រឈម', 'ប្រមាណ', 'ប្រហែល',
        'ប្រាំបី', 'ប្រាំបួន', 'ប្រាំមួយ', 'បំផុត', 'បំពេញ', 'ផង', 'ផុត', 'ផ្គាប់',
        'ផ្ដល់នូវ', 'ផ្ទុយនឹង', 'ផ្ទុយពី', 'ផ្សេងទៀត', 'ពី', 'ពីនេះតទៅ', 'ពីនេះពីនោះ',
        'ពីព្រោះ', 'ពីមុន', 'ពីរ', 'ពីលើ', 'ពុំ', 'ពួក', 'ពួកគេ', 'ពេញ', 'ពេញទាំង', 'ពេល',
        'ពេលដែល', 'ពេលនោះ', 'ពោលគឺ', 'ព្រោះ', 'ព្រោះតែ', 'ភាព', 'មក', 'មកកាន់', 'មកពី',
        'ម៉េច', 'មាន', 'មិនដែល', 'មិនត្រូវ', 'មិនទាន់', 'មិនទៀង', 'មិនព្រម', 'មិនមែន',
        'មិនអាច', 'មូល', 'មូលហេតុ', 'មួយ', 'មួយចំនួន', 'មួយណា', 'មួយទៀត', 'មែន',
        'មែនទែន', 'ម្ដង', 'ម្នាក់', 'ម្នាក់ៗ', 'ម្ភៃ', 'ម្យ៉ាងទៀត', 'ម្ល៉េះ', 'យក',
        'យកចេញ', 'យល់ស្រប', 'យ៉ាង', 'យ៉ាងច្រើន', 'យ៉ាងណា', 'យ៉ាងណាក៏ដោយ', 'យ៉ាងណាក្តី',
        'យ៉ាងនេះ', 'យ៉ាងនោះ', 'យើង', 'ឬ', 'រក្សា', 'រញៀវ', 'ឬទេ', 'របស់', 'របស់ខ្ញុំ',
        'របស់គាត់', 'របស់គេ', 'របស់នាង', 'របស់លោក', 'របស់វា', 'រយះពេល', 'រយៈ',
        'រយៈនេះ', 'រវាង', 'រហូតដល់', 'រាល់', 'រឺ', 'រឺក៏', 'រួចហើយ', 'រួម', 'រួមទាំង',
        'លើ', 'លើក', 'លើកលែង', 'លើស', 'លេខមួយ', 'លែង', 'លោក', 'ល្អ', 'លំអិត', 'វា',
        'វិញ', 'វែង', 'សព្វ', 'សម្រាប់', 'សរុប', 'សូម្បីតែ', 'សេចក្ដី', 'សោះ', 'ស្ងៀម',
        'ស្ទើរ', 'ស្មើរគ្នា', 'ស្មោះ', 'ស្វែងរក', 'សំខាន់', 'សំរាប់', 'សំរេច', 'ហាម', 'ហាសិប', 'ហុកសិប', 'ហើយ', 'ហើយនឹង', 'ហេតុផល', 'ហេតុអ្វី', 'ហៅ', 'ឡើង', 'ឡើយ',
        'ឯ', 'ឯការ', 'ឯកោ', 'អង្កាល់', 'អញ្ចឹង', 'ឯណា', 'ឥត', 'ឥតទៅណា', 'អតីត',
        'ឯទៀត', 'អស់', 'ឥឡូវនេះ', 'អ៊ីចឹង', 'អាច', 'អី', 'អោយ', 'អ្នក', 'អ្នកក្រោយ',
        'អ្នកណា', 'ឱ្យ', 'អ្វី', 'អ្វីខ្លះ', 'អ្វីមួយ', 'អំពី', '។ល។'
    ]
    return set(stop_words_list)

def load_stop_words_from_file(file_path):
    stop_words = set()
    try:
        with open(file_path, mode='r', encoding='utf-8') as file:
            reader = csv.reader(file)
            for row in reader:
                if row:
                    stop_words.add(row[0].strip())
    except FileNotFoundError:
        print(f"Error: Stop words file not found at {file_path}")
    return stop_words

def khfilter(text, stop_words=None):
    if stop_words is None:
        stop_words = get_default_stop_words()
    dictionary = get_khmer_dictionary().union(stop_words)
    words = longest_match_segmenter(text, dictionary)
    filtered_words = [word for word in words if word not in stop_words]
    return " ".join(filtered_words)

def khseg(text):
    dictionary = get_khmer_dictionary()
    return longest_match_segmenter(text, dictionary)

def khsyllable(text):
    return syllable_segmenter(text)

def khpos(text):
    try:
        from khmernltk import pos_tag as khmernltk_pos_tag
    except ImportError as exc:
        raise ImportError(
            "POS dependencies are unavailable. Install khmereasytools[khmernltk] "
            "(the distribution is named khmer-nltk)."
        ) from exc
    # POS tagging works best on space-separated text
    segmented_text = " ".join(khseg(text))
    return khmernltk_pos_tag(segmented_text)

def khocr(image_path):
    try:
        import pytesseract
        from PIL import Image
    except ImportError as exc:
        raise ImportError(
            "OCR dependencies not installed. Install khmereasytools[ocr]."
        ) from exc
    try:
        with Image.open(image_path) as image:
            return pytesseract.image_to_string(image, lang='khm')
    except FileNotFoundError:
        return f"Error: Image file not found at '{image_path}'"
    except Exception as e:
        return f"An OCR error occurred: {e}\n(Please ensure Tesseract is installed and 'khm' language data is available.)"

def is_khmer(text):
    return bool(re.search(u'[\u1780-\u17FF]', text))
