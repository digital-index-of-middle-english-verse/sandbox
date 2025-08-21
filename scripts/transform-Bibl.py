# This script transforms Bibliography.xml into valid CSL data.  Links to
# on-line facsimiles are sifted out, for separate handling tbd.
#
# Warnings are emitted for unexpected data structures or values. This pertains
# especially to values of `pubstmt`, a nasty free text field in the source XML.
#
# Any validation error emitted by jsonschema is written to the end of log file,
# after warnings thrown during conversion

import os
import xmltodict
import re
import yaml
import json
import jsonschema

# Top-level variables
source = '../../dimev/data/Bibliography.xml'
destination = '../artefacts/'
csl_schema = '../schemas/csl-data.json'
# test_sample= range(50)
warning_log = ['Warnings from the latest run of `transform-Bibl.py`.\n']
links_to_online_facs = []
log_file = '../artefacts/warnings.txt'

def read_xml_to_string(source):
    print(f'Reading source file `{source}` to string...')
    with open(source) as f:
        xml_string = f.read()
    print('Preprocessing string...')
    xml_string = re.sub(r' {2,}', ' ', xml_string) # remove whitespace
    xml_string = re.sub(r'\n', '', xml_string) # remove newlines
    xml_string = re.sub(r'<sup>', 'BEGIN_SUP', xml_string) # replace <sup> tags
    xml_string = re.sub(r'</sup>', 'END_SUP', xml_string)
    xml_string = re.sub(r'<i>', 'BEGIN_ITALICS', xml_string)  # replace <i> tags
    xml_string = re.sub(r'</i>', 'END_ITALICS', xml_string)
    return xml_string

def xml_to_dict(xml_string):
    print('Parsing string as a Python dictionary...')
    xml_dict = xmltodict.parse(xml_string)
    items = xml_dict['bibliography']['bibl'] # strip outer keys
    return items

def convert_item(sourceItem, warning_log):
    # Unclutter sourceItem
    if 'index' in sourceItem:
        sourceItem.pop('index') # NOTE: Ignore keywords, for now
    # Delete stray orphaned full stops
    if sourceItem.get('#text') == '.':
        sourceItem.pop('#text')

    # Define newItem
    newItem = {}
    newItem['id'] = sourceItem.get('@xml:id') # NOTE: could be mapped also to CSL:citation-key
    newItem['type'] = 'book' # set a default value for a required field

    for tag_name in sourceItem.keys():
        # process authorstmt
        if tag_name == 'authorstmt':
            authorstmt = sourceItem['authorstmt']
            if authorstmt is None:
                msg = f'WARNING: Empty `authorstmt` in item {sourceItem["@xml:id"]}.'
                # warning_log.append(msg)
            else: # process as dict
                for agent in ['author', 'editor', 'translator']: # the only valid children of 'authorstmt'
                    if agent in authorstmt:
                        if type(authorstmt[agent]) == dict:
                            authorstmt[agent] = [authorstmt[agent]] # force to list
                        newItem[agent] = convert_agents(authorstmt[agent], sourceItem['@xml:id'])

        # process titlestmt
        elif tag_name == 'titlestmt':
            if sourceItem['titlestmt'] is None:
                msg = f'WARNING: Empty `titlestmt` in item {sourceItem["@xml:id"]}.'
                warning_log.append(msg)
            else: # process as dict

                # Map 'vols' to CSL 'number-of-volumes'
                if 'vols' in sourceItem['titlestmt']:
                    newItem['number-of-volumes'] = sourceItem['titlestmt'].pop('vols')

                # Process titles
                titles = sourceItem['titlestmt']['title']
                if type(titles) == dict:
                    titles = [titles] # force to list

                # read title types
                title_types = []
                options = ['a', 'm', 'j', 's'] # "a"=Article "m"=Monograph "j"=Journal "s"=Series
                for title in titles:
                    if title['@level'] not in options:
                        msg = f'WARNING: unexpected title type found in item {sourceItem["@xml:id"]}'
                        print(msg)
                        warning_log.append(msg)
                    if title['@level'] in title_types:
                        msg = f'WARNING: duplicate title type found in item {sourceItem["@xml:id"]}'
                        print(msg)
                        warning_log.append(msg)
                    else:
                        title_types.append(title['@level'])
                
                # map titles to CSL
                for title in titles:
                    if title['@level'] == 'j':
                        newItem['type'] = 'article-journal'
                        newItem['container-title'] = title.pop('#text')
                    elif title['@level'] == 's':
                        if 'j' in title_types:
                            msg = f'WARNING: unexpected combination of title types found in item {sourceItem["@xml:id"]}'
                            print(msg)
                            warning_log.append(msg)
                        if 'a' in title_types and 'm' not in title_types:
                            msg = f'WARNING: unexpected combination of title types found in item {sourceItem["@xml:id"]}'
                            print(msg)
                            warning_log.append(msg)
                        newItem['type'] = 'book'
                        newItem['collection-title'] = title.pop('#text')
                    elif title['@level'] == 'm':
                        # get book title and URLs
                        if 'ref' in title:
                            this_book_title, url = process_ref(title)
                            newItem['URL'] = url
                        if '#text' in title:
                            this_book_title = format_string(title.pop('#text'))
                        # assign type and title
                        if 'j' in title_types:
                            msg = f'WARNING: unexpected combination of title types found in item {sourceItem["@xml:id"]}'
                            print(msg)
                            warning_log.append(msg)
                        elif 'a' in title_types:
                            newItem['type'] = 'chapter'
                            newItem['container-title'] = this_book_title
                        else:
                            newItem['type'] = 'book'
                            newItem['title'] = this_book_title
                    else: # if title['@level'] == 'a':
                        if '#text' in title:
                            newItem['title'] = format_string(title.pop('#text'))
                        if 'ref' in title:
                            this_title, url = process_ref(title)
                            newItem['title'] = this_title
                            newItem['URL'] = url

        # process pubstmt
        elif tag_name == 'pubstmt':
            pubstmt = sourceItem['pubstmt']
            if pubstmt is None:
                msg = f'WARNING: Empty `pubstmt` in item {sourceItem["@xml:id"]}.'
                print(msg)
                warning_log.append(msg)
            elif type(pubstmt) is not dict:
                msg = f'WARNING: Unexpected data type for `pubstmt` in item {sourceItem["@xml:id"]}.'
                print(msg)
                warning_log.append(msg)
            else: # process pubstmt
                # process the date attribute
                if '@date' not in pubstmt:
                    msg = f'WARNING: No `@date` attribute in item {sourceItem["@xml:id"]}'
                    print(msg)
                    warning_log.append(msg)
                elif pubstmt['@date'].lower() == 'n.d.' or pubstmt['@date'] == '':
                    msg = f'WARNING: No date value found for `@date` attribute in item {sourceItem["@xml:id"]}'
                    warning_log.append(msg)
                elif re.search(r'[A-Za-z=\?\+]', pubstmt['@date']):
                    msg = f'WARNING: Invalid value found for `@date` attribute in item {sourceItem["@xml:id"]}. Skipping.'
                    print(msg)
                    warning_log.append(msg)
                elif re.search(r'\d{5,}', pubstmt['@date']):
                    msg = f'WARNING: Invalid value found for `@date` attribute in item {sourceItem["@xml:id"]}. Skipping.'
                    print(msg)
                    warning_log.append(msg)
                elif len(pubstmt['@date']) < 4:
                    msg = f'WARNING: Invalid value found for `@date` attribute in item {sourceItem["@xml:id"]}. Skipping.'
                    print(msg)
                    warning_log.append(msg)
                else:
                    # Extract four-digit publication years from the '@date' attribute
                    date_from_attr = pubstmt['@date']
                    date_dict = create_date_dict(date_from_attr)
                    if date_dict['date-parts'] == []:
                        msg = 'WARNING: Unsupported date pattern in item {sourceItem["@xml:id"]}. Skipping.'
                        print(msg)
                        warning_log.append(msg)
                    else:
                        newItem['issued'] = date_dict

                # Process the `#text` element
                if '#text' not in pubstmt:
                    msg = f'WARNING: No text value for `pubstmt` in item {sourceItem["@xml:id"]}. Skipping.'
                    print(msg)
                    warning_log.append(msg)
                else:
                    pubstmt_str = pubstmt['#text']

                    # Identify and process dissertations and theses
                    if 'Diss.' in pubstmt_str or 'thesis' in pubstmt_str:
                        newItem = format_theses(newItem, pubstmt_str)

                    # Process journal articles
                    elif newItem['type'] == 'article-journal':
                        if ':' in pubstmt_str:
                            parts = re.split(':', pubstmt_str, maxsplit=1)
                            newItem['volume'] = re.sub(r'\(.*\d\d\d\d.*\)', '', parts[0]).strip()
                            newItem['page'] = parts[1].strip()
                        else:
                            msg = f'WARNING: Irregular pubstmt found for journal-article {sourceItem["@xml:id"]}. Skipping.'
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

    # Reconcile dates
    extracted_date_dict = create_date_dict(date_str)
    if 'issued' in newItem.keys() and newItem['issued'] != extracted_date_dict:
        if extracted_date_dict['date-parts'] is not None and extracted_date_dict['date-parts'] != []:
            newItem['issued'] = extracted_date_dict
            # if newItem['issued']['date-parts'][0][0] != extracted_date_dict['date-parts'][0][0]:
            #     msg = f'WARNING: discrepant dates for item {newItem["id"]}'
            #     warning_log.append(msg)

    return newItem, warning_log

def process_ref(title):
    if '#text' in title['ref']:
        this_book_title = format_string(title['ref'].pop('#text'))
    if title['ref'].get('@type', '') == 'url':
        if title['ref'].get('@n', '') != '':
            url = title['ref'].pop('@n')
            title['ref'].pop('@type')
    return this_book_title, url

def create_date_dict(date_str):
    # NOTE: I use the 'more structured' representation of dates permitted by the CSL spec.
    date_str = re.sub(r'\[|\]', '', date_str) # NOTE: strip brackets, for now
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

def convert_agents(agents, itemID):
    nameList = []
    for nomen in agents:
        nameParts = {}
        nameParts['family'] = nomen.pop('last', '')
        if 'first' in nomen and nomen['first'] is not None:
            nameParts['given'] = nomen.pop('first', '')
        # Remove stray orphaned punctuation
        if nomen.get('#text', '') in ['.', ',']:
            nomen.pop('#text')
        # Ignore titles of nobility, academic degree
        if nomen.get('prefix', '') in ['Dr.', 'Sir', 'Lord']:
            nomen.pop('prefix')
        nameList.append(nameParts)
    return nameList

def format_string(value):
    if type(value) == str:
        value = re.sub('BEGIN_ITALICS', '<i>', value)
        value = re.sub('END_ITALICS', '</i>', value)
        value = re.sub('BEGIN_SUP', '<sup>', value)
        value = re.sub('END_SUP', '</sup>', value)
    return value

def validate_items(conversion):
    print(f'Validating YAML conversion...')
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
    output_filename = destination + 'bibliography.json'
    with open(output_filename, 'w') as f:
        json.dump(conversion, f, sort_keys=False, ensure_ascii=False, indent=2)
    print(f'Wrote conversion to `{output_filename}`.')

# Workflow

# read the source file to string and pre-process
xml_string = read_xml_to_string(source)

# create a dictionary
items = xml_to_dict(xml_string)
count_items = len(items)
print(f'Found {count_items} items.')

# Sort and convert items
if not 'test_sample' in locals():
    test_sample = range(len(items)) # Convert all items, unless a test_sample is specified previously
conversion = []
for idx in test_sample:
    # Walk the tree; if the item is a link to an on-line facsimile, toss aside for future processing. These are not converted to CSL format
    conditionsA = 'pubstmt' in items[idx] \
                 and 'titlestmt' in items[idx] \
                 and 'title' in items[idx]['titlestmt'] \
                 and 'ref' in items[idx]['titlestmt']['title'] \
                 and 'Digital Facsimile of' in items[idx]['titlestmt']['title']['ref'].get('#text', '')
    conditionsB1 = type(items[idx]['pubstmt']) == dict \
                 and 'http' in items[idx]['pubstmt'].get('#text', '')
    conditionsB2 = type(items[idx]['pubstmt']) == str \
                 and 'http' in items[idx]['pubstmt']
    if conditionsA and conditionsB1:
        links_to_online_facs.append(items[idx])
    elif conditionsA and conditionsB2:
        links_to_online_facs.append(items[idx])
    # Convert item
    else:
        newItem, warning_log = convert_item(items[idx], warning_log)
        conversion.append(newItem)

# Validate and write
validate_items(conversion)

count_warnings = len(warning_log) - 1

msg = f'Conversions completed with {count_warnings} warnings \
and {len(links_to_online_facs)} unconverted links to on-line facsimiles.'
print(msg)
print('Wrote log to ../artefacts/warnings.txt')

warning_log.append(msg)
with open(log_file, 'w') as file:
    for line in warning_log:
        file.write(line + '\n')

write_to_file(conversion)
