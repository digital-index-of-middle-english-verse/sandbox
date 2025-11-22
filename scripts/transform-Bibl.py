# This script transforms Bibliography.xml into valid CSL data.  Links to
# on-line facsimiles are sifted out, for separate handling.
#
# Warnings are emitted for unexpected data structures or values. This pertains
# especially to values of `pubstmt`, a nasty free text field in the source XML.
#
# Any validation error emitted by jsonschema is written to the end of log file,
# after warnings thrown during conversion

import os
import re
import json
import jsonschema
from lxml import etree

# Top-level variables
source_dir = '../../dimev/data/'
source_file = 'Bibliography.xml'
dest_dir = '../artefacts/'
csl_schema = '../schemas/csl-data.json'
log_file = 'warnings.txt'
namespace = '{http://www.w3.org/XML/1998/namespace}'

def main():
    tree = etree.parse(source_dir + source_file)
    root = tree.getroot()
    bibl = root.findall('bibl')
    print(f'Found {len(bibl)} items.')

    csl_items = [] # Empty container for converted items
    online_facs_keys = [] # Empty container for keys of online facsimiles
    warning_log = ['Warnings from the latest run of `transform-Bibl.py`.\n']

    for item in bibl:

        # If the item is a link to an on-line facsimile, toss aside for future
        # processing. These are not converted to CSL format
        facs, online_facs_keys = extract_online_facs(item, online_facs_keys)
        if not facs: # Convert item
            converted_item, warning_log = convert_item(item, warning_log)
            csl_items.append(converted_item)

    # Validate and write
    validate_csl(csl_items, warning_log)
    report_warnings(warning_log, online_facs_keys)
    write_to_file(csl_items)
    print('Done')
    
def extract_online_facs(item, online_facs_keys):
    # NOTE: The logic here is identical with that in update-Manuscripts.py.
    # That file runs a check against an earlier output of this script, prior to
    # refactoring. Since the two logics have identical results, I use the
    # simpler one.

    facs = False
    bib_key = item.get(namespace + 'id')
    pubstmt = item.find('pubstmt')
    pubstmt_text = etree.tostring(pubstmt, encoding='unicode', method='text')
    if 'http' in pubstmt_text:
        facs = True
        online_facs_keys.append(bib_key)
    return facs, online_facs_keys

def convert_item(sourceItem, warning_log):
    # NOTE: We ignore contents of the index element

    # Define newItem
    newItem = {}
    newItem['id'] = sourceItem.get(namespace + 'id') # NOTE: could be mapped also to CSL:citation-key
    newItem['type'] = 'book' # set a default value for a required field

    # Convert authorstmt, if present
    authorstmt = sourceItem.find('authorstmt')
    if authorstmt is not None:
        newItem = convert_authorstmt(authorstmt, newItem)
    else:
        msg = f'WARNING: Empty `authorstmt` in item {bibkey}.'
        warning_log.append(msg)

    # Convert titlestmt, if present
    titlestmt = sourceItem.find('titlestmt')
    if titlestmt is not None:
        newItem, warning_log = convert_titlestmt(titlestmt, newItem, warning_log)
    else:
        msg = f'WARNING: Empty `titlestmt` in item {bibkey}.'
        warning_log.append(msg)

    # Convert pubstmt, if present
    pubstmt = sourceItem.find('pubstmt')
    if pubstmt is not None:
        newItem, warning_log = convert_pubstmt(pubstmt, newItem, warning_log)
    else:
        msg = f'WARNING: Empty `pubstmt` in item {bibkey}.'
        warning_log.append(msg)

    return newItem, warning_log

def convert_authorstmt(authorstmt, newItem):
    for agent in ['author', 'editor', 'translator']: # the only valid children of 'authorstmt'
        agent_list = authorstmt.findall(agent)
        if agent_list is not None:
            name_list = convert_agents(agent_list)
            if len(name_list) > 0:
                newItem[agent] = name_list
    return newItem

def convert_titlestmt(titlestmt, newItem, warning_log):

    # Map 'vols' to CSL 'number-of-volumes'
    number_of_volumes = titlestmt.find('vols')
    if number_of_volumes is not None:
        newItem['number-of-volumes'] = number_of_volumes.text.strip()

    # Process titles
    level_vals = []
    options = ['a', 'm', 'j', 's'] # "a"=Article "m"=Monograph "j"=Journal "s"=Series
    title_list = titlestmt.findall('title')

    # First, gather values of 'level'

    for title in title_list:
        title_level = title.get('level')
        if title_level in level_vals:
            msg = f'WARNING: duplicate title type found for item {newItem["id"]}. Values will be overwritten'
            print(msg)
            warning_log.append(msg)
        else:
            level_vals.append(title_level)

    # Next, test for illegal combinations of title levels
    warn_conditions = [
            's' in level_vals and 'j' in level_vals, # series title and journal title
            's' in level_vals and 'a' in level_vals and 'm' not in level_vals, # series title, chapter title, but not monograph title
            'm' in level_vals and 'j' in level_vals # monograph title and journal title
            ]
    if any(warn_conditions):
        msg = f'WARNING: unexpected combination of title types found for item {newItem["id"]}'
        print(msg)
        warning_log.append(msg)

    # Finally, test for unexpected level values and convert passing titles
    for title in title_list:
        if title_level in options:
            # Convert to CSL
            newItem = process_title(title, level_vals, newItem)
        else:
            msg = f'WARNING: unexpected title type found for item {newItem["id"]}. Skipping'
            print(msg)
            warning_log.append(msg)

    return newItem, warning_log

def process_title(title, level_vals, newItem):
    title_level = title.get('level')

    # Inspect and process title content
    if title.find('ref') is None:
        # Force to string (to preserve inset <i> elements)
        title_text = stringify_content(title)
    else:
        ref = title.find('ref')
        # Add URL
        newItem['URL'] = ref.get('n')
        # Force to string (to preserve inset <i> and <sup> elements)
        title_text = stringify_content(ref)

    # Map to CSL
    if title_level == 'j':
        newItem['type'] = 'article-journal'
        newItem['container-title'] = title_text
    elif title_level == 's':
        newItem['type'] = 'book'
        newItem['collection-title'] = title_text
    elif title_level == 'm':
        if 'a' in level_vals:
            newItem['type'] = 'chapter'
            newItem['container-title'] = title_text
        else:
            newItem['type'] = 'book'
            newItem['title'] = title_text
    else: # title_level == 'a'
        newItem['title'] = title_text

    return newItem

def stringify_content(element):
    parts = []
    if len(element):
        # Iterate through children and their tails, excluding coments
        for child in element.iter(tag=etree.Element):
            if child.tag == 'title' or child.tag == 'ref':
                parts.append(f"{child.text.strip() if child.text else ''}")
            else: # Add the child's tag and its text
                parts.append(f"<{child.tag}>{child.text.strip() if child.text else ''}</{child.tag}>")
            # Add the text following the child
            if child.tail:
                parts.append(child.tail.strip())
        string = ' '.join(parts).strip()
        string = re.sub(r'> ([,:\)\?])', r'>\1', string)
        string = re.sub('En <sup>', 'En<sup>', string) # A single case
        string = remove_whitespace(string)
        if string == "Epitaphs, &c. ( <i>To the Editor of the Mirror.</i>)":
            string = "Epitaphs, &c. (<i>To the Editor of the Mirror.</i>)"
    else:
        string = remove_whitespace(element.text).strip()
    return string

def remove_whitespace(text_str):
    text_str = re.sub(' {2,}', ' ', text_str)
    text_str = re.sub(r'\n', '', text_str)
    return text_str

def convert_pubstmt(pubstmt, newItem, warning_log):
    # Process the date attribute
    date_val = pubstmt.get('date')
    newItem, warning_log = process_date_from_attr(date_val, newItem, warning_log)

    # Process text content. pubstmt permits only string content and comment elements
    pubstmt_str = etree.tostring(pubstmt, encoding='unicode', method='text').strip()
    pubstmt_str = remove_whitespace(pubstmt_str)

    # Identify and process dissertations and theses
    if 'Diss.' in pubstmt_str or 'thesis' in pubstmt_str:
        newItem = format_theses(newItem, pubstmt_str)

    # Process journal articles
    elif newItem['type'] == 'article-journal':
        if ':' in pubstmt_str:
            # NOTE: The script does not disaggregate volume and number
            parts = re.split(':', pubstmt_str, maxsplit=1)
            newItem['volume'] = re.sub(r'\(.*\d\d\d\d.*\)', '', parts[0]).strip()
            newItem['page'] = parts[1].strip()
        else:
            msg = f'WARNING: Irregular pubstmt found for journal-article {newItem["id"]}. Skipping.'
            print(msg)
            warning_log.append(msg)

    # Process books
    elif newItem['type'] == 'book':
        newItem, warning_log = parse_pubstmt_books(newItem, pubstmt_str, warning_log)

    # Process book chapters
    # First, extract page ranges where present; then parse with the same logic used for items of type 'book'
    elif newItem['type'] == 'chapter':
        pattern = r'\d\d\d\d(-\d{1,4})?[:,\.] \d+(-\d+)?$'
        if re.search(pattern, pubstmt_str):
            newItem['page'] = re.sub(r'^.*\d\d\d\d(-\d{1,4})?[:,\.] ', '', pubstmt_str)
            pubstmt_str = re.sub(r'[:,\.] \d+(-\d+)?$', '', pubstmt_str)
        newItem, warning_log = parse_pubstmt_books(newItem, pubstmt_str, warning_log)

    else:
        msg = f'WARNING: Unrecognized CSL type for transform of {sourceItem["@xml:id"]}.'
        print(msg)
        warning_log.append(msg)

    return newItem, warning_log

def process_date_from_attr(date_val, newItem, warning_log):
    warn_conditions = [
            date_val.lower == 'n.d',
            date_val == '',
            re.search(r'[A-Za-z=\?\+]', date_val),
            re.search(r'\d{5,}', date_val),
            len(date_val) < 4
        ]
    if date_val is None:
        msg = f'WARNING: No `date` attribute in item {newItem["id"]}'
        print(msg)
        warning_log.append(msg)
    elif any(warn_conditions):
        msg = f'WARNING: Invalid value found for `date` attribute in item {newItem["id"]}. Skipping.'
        print(msg)
        warning_log.append(msg)
    else: # Extract four-digit publication years from the '@date' attribute
        date_dict = create_date_dict(date_val)
        if date_dict['date-parts'] == []:
            msg = 'WARNING: Unsupported date pattern in item {newItem["id"]}. Skipping.'
            print(msg)
            warning_log.append(msg)
        else:
            newItem['issued'] = date_dict
    return newItem, warning_log

def parse_pubstmt_books(newItem, pubstmt_str, warning_log):
    # pre-process
    pubstmt_str = re.sub(r'[;,] repr\. \d\d\d\d(\)?)$', r'\1', pubstmt_str) # strip out reprint dates
    pubstmt_str = re.sub(', and subsequent editions', '', pubstmt_str)
    pubstmt_str = re.sub(r',? et seq\.?', '', pubstmt_str)
    if re.match(r'^rev\. ed\.', pubstmt_str):
        newItem['edition'] = 'revised'
        pubstmt_str = re.sub(r'^rev\. ed\.,? ', '', pubstmt_str)
    # set variables
    date_pattern = r'(\d\d\d\d[\d\-, ]*)' # imprecise but it works
    place_pattern = r'([A-Z\[][A-Za-zäöü &,\-]+[A-Za-z\]\.])'
    publisher_pattern = r'([A-Za-z][A-Za-zäöüé’ &/,\.\-]+[A-Za-zé\.])'
    series_numb_patt = r'(\d*[0-9 ,\-]+\d*)'
    vol_pattern = r'((V|v)ol\.? [1-9]+)'
    # Date only
    if re.fullmatch(r'\(?' + date_pattern + r'\)?', pubstmt_str):
        date_str = re.sub(r'\(|\)', '', pubstmt_str)
        msg = f'WARNING: No publisher or publisher place for monograph {newItem["id"]}'
        # warning_log.append(msg)
    # Series number. Date
    elif re.fullmatch(series_numb_patt + r' ?\(?' + date_pattern + r'\)?', pubstmt_str):
        this_pattern = '^' + series_numb_patt + r' ?\(?' + date_pattern + r'\)?$'
        newItem['collection-number'] = re.sub(this_pattern, r'\1', pubstmt_str).strip()
        date_str = re.sub(this_pattern, r'\2', pubstmt_str)
        msg = f'WARNING: No publisher or publisher place for monograph {newItem["id"]}'
        # warning_log.append(msg)
    # Volume number. Place, Date
    elif re.fullmatch(vol_pattern + r'\. ' + place_pattern + ', ' + date_pattern, pubstmt_str):
        substring = re.sub(', ' + date_pattern + '$', '', pubstmt_str)
        newItem['publisher-place'] = re.sub(vol_pattern + r'\. ', '', substring)
        newItem['volume'] = re.sub(r'(V|v)ol\.? ([1-9]+)\. .*', r'\2', substring)
        date_str = re.sub(vol_pattern + r'\. ' + place_pattern + ', ' + date_pattern, r'\3', pubstmt_str)
    # Place, Date
    elif re.fullmatch(place_pattern + ', ' + date_pattern, pubstmt_str):
        this_pattern = '^' + place_pattern + ', ' + date_pattern + '$'
        newItem['publisher-place'] = re.sub(this_pattern, r'\1', pubstmt_str).strip()
        date_str = re.sub(this_pattern, r'\2', pubstmt_str)
    # Edition number. Place, Date
    elif re.fullmatch(r'[1-9].. ed\.,? ' + place_pattern + ', ' + date_pattern, pubstmt_str):
        this_pattern = '^' + r'([1-9]).. ed\.,? ' + place_pattern + ', ' + date_pattern + '$'
        newItem['edition'] = re.sub(this_pattern, r'\1', pubstmt_str)
        newItem['publisher-place'] = re.sub(this_pattern, r'\2', pubstmt_str).strip()
        date_str = re.sub(this_pattern, r'\3', pubstmt_str)
    # Publisher: Date
    elif re.fullmatch(publisher_pattern + ': ' + date_pattern, pubstmt_str):
        parts = re.split(':', pubstmt_str)
        newItem['publisher'] = parts[0]
        date_str = parts[1]
    # Series number. Publisher: Date
    elif re.fullmatch(series_numb_patt + r'[\.,]? ' + publisher_pattern + ': ' + date_pattern, pubstmt_str):
        parts = re.split(':', pubstmt_str)
        this_pattern = '^' + series_numb_patt + r'[\.,]? ' + publisher_pattern + '$'
        newItem['collection-number'] = re.sub(this_pattern, r'\1', parts[0]).strip()
        newItem['publisher'] = re.sub(this_pattern, r'\2', parts[0]).strip()
        date_str = parts[1]
    # Series number. Place, Date
    elif re.fullmatch(series_numb_patt + r'[\.,]? ' + place_pattern + ', ' + date_pattern, pubstmt_str):
        this_pattern = '^' + series_numb_patt + r'[\.,]? ' + place_pattern + ', ' + date_pattern + '$'
        newItem['collection-number'] = re.sub(this_pattern, r'\1', pubstmt_str).strip()
        newItem['publisher-place'] = re.sub(this_pattern, r'\2', pubstmt_str).strip()
        date_str = re.sub(this_pattern, r'\3', pubstmt_str)
    # Place: Publisher, Date
    elif re.fullmatch(place_pattern + ': ' + publisher_pattern + ', ' + date_pattern, pubstmt_str):
        parts = re.split(':', pubstmt_str)
        newItem['publisher-place'] = parts[0].strip()
        newItem['publisher'] = re.sub(', ' + date_pattern + '$', '', parts[1]).strip()
        date_str = re.sub(publisher_pattern + ', ', '', parts[1])
    # Edition number. Place: Publisher, Date
    elif re.fullmatch(r'[1-9].. ed\. ' + place_pattern + ': ' + publisher_pattern + ', ' + date_pattern, pubstmt_str):
        parts = re.split(':', pubstmt_str)
        newItem['edition'] = re.sub(r' ed\..+', '', parts[0])
        newItem['publisher-place'] = re.sub(r'[1-9].. ed\. ', '', parts[0])
        newItem['publisher'] = re.sub(', ' + date_pattern + '$', '', parts[1]).strip()
        date_str = re.sub(publisher_pattern + ', ', '', parts[1])
    # Volume number. Place: Publisher, Date
    elif re.fullmatch(vol_pattern + r'\. ' + place_pattern + ': ' + publisher_pattern + ', ' + date_pattern, pubstmt_str):
        parts = re.split(':', pubstmt_str)
        newItem['volume'] = re.sub(r'(V|v)ol\.? ([1-9]+)\. .*', r'\2', parts[0])
        newItem['publisher-place'] = re.sub(vol_pattern + r'\. ', '', parts[0])
        newItem['publisher'] = re.sub(', ' + date_pattern + '$', '', parts[1]).strip()
        date_str = re.sub(publisher_pattern + ', ', '', parts[1])
    # Series number. Place: Publisher, Date
    elif re.fullmatch(series_numb_patt + r'[\.,]? ' + place_pattern + ': ' + publisher_pattern + ', ' + date_pattern, pubstmt_str):
        parts = re.split(':', pubstmt_str)
        newItem['collection-number'] = re.sub(series_numb_patt + r'[\.,]? ' + place_pattern, r'\1', parts[0]).strip()
        newItem['publisher-place'] = re.sub(series_numb_patt + r'[\.,]? ' + place_pattern, r'\2', parts[0]).strip()
        newItem['publisher'] = re.sub(publisher_pattern + ', ' + date_pattern, r'\1', parts[1]).strip()
        date_str = re.sub(publisher_pattern + ', ' + date_pattern, r'\2', parts[1])
    # All other patterns
    else:
        msg = f'WARNING: Unprocessed `pubstmt` for item {newItem["id"]}: "{pubstmt_str}"'
        warning_log.append(msg)
        newItem['publisher'] = pubstmt_str
        date_str = ''

    # NOTE: The date extracted from pubstmt content is preferred. This is
    # probably ok, as I checked discrepancies item-by-item when first
    # implemented

    extracted_date_dict = create_date_dict(date_str)
    if 'issued' in newItem.keys() and newItem['issued'] != extracted_date_dict:
        if extracted_date_dict['date-parts'] is not None and extracted_date_dict['date-parts'] != []:
            newItem['issued'] = extracted_date_dict
            if newItem['issued']['date-parts'][0][0] != extracted_date_dict['date-parts'][0][0]:
                 msg = f'WARNING: discrepant dates for item {newItem["id"]}'
                 warning_log.append(msg)

    return newItem, warning_log

def create_date_dict(date_str):
    # NOTE: I use the 'more structured' representation of dates permitted by the CSL spec.
    date_str = re.sub(r'\[|\]', '', date_str) # NOTE: strip brackets
    date_str = date_str.strip()
    if re.search(r'^\d\d\d\d$', date_str):
        date_list = [[int(date_str)]]
    elif '-' in date_str:
        date_list = uncollapse_date_ranges(date_str)
    elif ', ' in date_str:
        date_list = date_str.split(', ')
        date_list.sort()
        date_list = [[int(date_list[0])], [int(date_list[-1])]]
    else:
        date_list = []
    date_dict = {'date-parts': date_list}
    return date_dict

def uncollapse_date_ranges(date_str):
    range_patterns = \
        [
            (r'^\d\d\d\d-\d$', r'^(\d\d\d\d)-\d$', r'^(\d\d\d)\d-(\d)$'),
            (r'^\d\d\d\d-\d\d$', r'^(\d\d\d\d)-\d\d$', r'^(\d\d)\d\d-(\d\d)$'),
            (r'^\d\d\d\d-\d\d\d\d$', r'^(\d\d\d\d)-\d\d\d\d$', r'^\d\d\d\d-(\d\d)(\d\d)$')
        ]
    for idx in range(len(range_patterns)):
        pattern = range_patterns[idx][0]
        regexMatch = re.search(pattern, date_str)
        if regexMatch:
            year = re.sub(range_patterns[idx][1], r'\1', date_str)
            date_list = [[int(year)]]
            year = re.sub(range_patterns[idx][2], r'\1\2', date_str)
            date_list.append([int(year)])
            return date_list

def format_theses(newItem, string):
    newItem['type'] = 'thesis'
    if 'Diss.' in string:
        newItem['genre'] = 'Ph.D. diss.'
        string = re.sub(r'Diss\. ', '', string)

    elif 'B.Litt.' in string:
        newItem['genre'] = 'B.Litt. thesis'
        string = re.sub(r'B\.Litt\. thesis\.', '', string)

    else: # 'thesis', two items only
        newItem['genre'] = 'M.A. thesis'
        string = re.sub(r'MA thesis\. ', '', string)
        string = re.sub(r'M\.Litt thesis\. ', '', string)

    string = re.sub(r', \d\d\d\d', '', string)
    newItem['publisher'] = string.strip()

    return newItem

def convert_agents(agent_list):
    # Ignore titles of nobility, academic degree
    new_list = []
    for agent in agent_list:
        nameParts = {}
        lastname = agent.find('last')
        if lastname is not None and lastname.text is not None:
            nameParts['family'] = lastname.text.strip()
        firstname = agent.find('first')
        if firstname is not None and firstname.text is not None:
            nameParts['given'] = firstname.text.strip()
        new_list.append(nameParts)
    return new_list

def validate_csl(conversion, warning_log):
    print(f'Validating JSON conversion...')
    with open(csl_schema) as f:
        schema = json.load(f)
    try:
        jsonschema.validate(instance=conversion, schema=schema)
        print('  Validation passing.\n')
        return True
    except jsonschema.ValidationError as e:
        print(f'  WARNING: Validation failed. See `{log_file}` for details.\n')
        warning_log.append('Validation report:\n')
        warning_log.append(str(e))
        return False

def write_to_file(conversion):
    output_filename = dest_dir + 'bibliography.json'
    with open(output_filename, 'w') as f:
        json.dump(conversion, f, sort_keys=False, ensure_ascii=False, indent=2)
    print(f'Wrote conversion to `{output_filename}`.')

def report_warnings(warning_log, online_facs_keys):
    count_warnings = len(warning_log) - 1

    msg = f'Conversions completed with {count_warnings} warnings and {len(online_facs_keys)} unconverted links to on-line facsimiles.'
    print(msg)
    warning_log.append(msg)

    with open(dest_dir + log_file, 'w') as file:
        for line in warning_log:
            file.write(line + '\n')
    print(f'Wrote warning log to {log_file}')

main()
