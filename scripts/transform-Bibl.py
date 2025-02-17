# This script attempts to transform Bibliography.xml into valid CSL data.
# Links to on-line facsimiles are sifted out, for separate handling tbd.
#
# Warnings are emitted for unexpected data structures or values.
#
# Any validation error emitted by jsonschema is written to the end of log file,
# after warnings thrown during conversion
#
# TODO: improve processing, disaggregation of `pubstmt` (a nasty free text
# field in the source XML)
#
# TODO: improve processing of dates. Extract date range from `pubstmt` content
# where that field is more accurate than the `date` attribute
#
# TODO: decide how to handle reprints

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
    xml_string = re.sub(' {2,}', ' ', xml_string) # remove whitespace
    xml_string = re.sub('\\n', '', xml_string) # remove newlines
    xml_string = re.sub('<sup>', 'BEGIN_SUP', xml_string) # replace <sup> tags
    xml_string = re.sub('</sup>', 'END_SUP', xml_string)
    xml_string = re.sub('<i>', 'BEGIN_ITALICS', xml_string)  # replace <i> tags
    xml_string = re.sub('</i>', 'END_ITALICS', xml_string)
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
    newItem['id'] = sourceItem.get('@xml:id')
    newItem['type'] = 'book' # set a default value for a required field

    for tag_name in sourceItem.keys():
        # process authorstmt
        if tag_name == 'authorstmt':
            authorstmt = sourceItem['authorstmt']
            if authorstmt is None:
                msg = f'WARNING: Empty `authorstmt` in item {sourceItem["@xml:id"]}.'
                warning_log.append(msg)
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
                elif re.search('[A-Za-z=\?\+]', pubstmt['@date']):
                    msg = f'WARNING: Invalid value found for `@date` attribute in item {sourceItem["@xml:id"]}. Skipping.'
                    print(msg)
                    warning_log.append(msg)
                elif re.search('\d{5,}', pubstmt['@date']):
                    msg = f'WARNING: Invalid value found for `@date` attribute in item {sourceItem["@xml:id"]}. Skipping.'
                    print(msg)
                    warning_log.append(msg)
                elif len(pubstmt['@date']) < 4:
                    msg = f'WARNING: Invalid value found for `@date` attribute in item {sourceItem["@xml:id"]}. Skipping.'
                    print(msg)
                    warning_log.append(msg)
                else:
                    # Extract four-digit publication years from the '@date' attribute
                    dateValue = pubstmt['@date']
                    dateValue = re.sub('\[|\]', '', dateValue) # NOTE: strip brackets, for now
                    dateValue = dateValue.strip() # strip leading and trailing whitespace characters
                    # NOTE: I use the 'more structured' representation of dates permitted by the CSL spec.
                    dateList = []
                    pattern = '^\d\d\d\d$'
                    regexMatch = re.search(pattern, dateValue)
                    if regexMatch:
                        year = pubstmt.pop('@date')
                        dateList = format_dates(year, dateList)
                        dateObject = {'date-parts': dateList}
                        newItem['issued'] = dateObject
                    elif '-' in dateValue:
                        dateList = uncollapse_date_ranges(dateValue, dateList)
                        dateObject = {'date-parts': dateList}
                        newItem['issued'] = dateObject
                    else:
                        msg = 'WARNING: Unsupported date pattern in item {sourceItem["@xml:id"]}. Skipping.'
                        print(msg)
                        warning_log.append(msg)

                # Process the `#text` element
                # NOTE: this is error-prone and inelegant
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
                            newItem['volume'] = re.sub('\(.*\d\d\d\d.*\)', '', parts[0]).strip()
                            newItem['page'] = parts[1].strip()
                        else:
                            msg = f'WARNING: Irregular pubstmt found for journal-article {sourceItem["@xml:id"]}. Skipping.'
                            print(msg)
                            warning_log.append(msg)

                    # Process books
                    elif newItem['type'] == 'book':
                        date_str = '[0-9\-, ]{4,}'
                        place_str = '([A-Z][A-Za-z ,]+[A-Za-z])'
                        publisher_str = '([A-Z][A-Za-z &/\.]+[A-Za-z])'
                        volume_str = '(\d*[0-9 ,]+\d*)'
                        # Date only
                        if re.fullmatch('\(?' + date_str + '\)?', pubstmt_str):
                            msg = f'WARNING: No publisher or publisher place for monograph {sourceItem["@xml:id"]}'
                            warning_log.append(msg)
                        # Volume number. Date
                        elif re.fullmatch(volume_str + '\(?' + date_str + '\)?', pubstmt_str):
                            newItem['collection-number'] = re.sub('^' + volume_str + '\(?' + date_str + '\)?$', r'\1', pubstmt_str).strip()
                            msg = f'WARNING: No publisher or publisher place for monograph {sourceItem["@xml:id"]}'
                            warning_log.append(msg)
                        # Place, Date
                        elif re.fullmatch(place_str + ', ' + date_str, pubstmt_str):
                            parts = re.split(',', pubstmt_str)
                            newItem['publisher-place'] = parts[0]
                        # Publisher: Date
                        elif re.fullmatch(publisher_str + ': ' + date_str, pubstmt_str):
                            parts = re.split(':', pubstmt_str)
                            newItem['publisher'] = parts[0]
                        # Vol number. Publisher: Date
                        elif re.fullmatch(volume_str + '[\.,]? ' + publisher_str + ': ' + date_str, pubstmt_str):
                            newItem['collection-number'] = re.sub('^' + volume_str + '[\.,]? ' + publisher_str + ': ' + date_str + '$', r'\1', pubstmt_str).strip()
                            newItem['publisher'] = re.sub('^' + volume_str + '[\.,]? ' + publisher_str + ': ' + date_str + '$', r'\2', pubstmt_str).strip()
                        # Vol number. Place, Date
                        elif re.fullmatch(volume_str + '[\.,]? ' + place_str + ', ' + date_str, pubstmt_str):
                            newItem['collection-number'] = re.sub('^' + volume_str + '[\.,]? ' + place_str + ', ' + date_str + '$', r'\1', pubstmt_str).strip()
                            newItem['publisher-place'] = re.sub('^' + volume_str + '[\.,]? ' + place_str + ', ' + date_str + '$', r'\2', pubstmt_str).strip()
                        # Place: Publisher, Date
                        elif re.fullmatch(place_str + ': ' + publisher_str + ', ' + date_str, pubstmt_str):
                            parts = re.split(':', pubstmt_str)
                            newItem['publisher-place'] = parts[0].strip()
                            publisher = re.sub(',.*', '', parts[1])
                            newItem['publisher'] = publisher.strip()
                        # Vol number. Place: Publisher, Date
                        elif re.fullmatch(volume_str + '[\.,]? ' + place_str + ': ' + publisher_str + ', ' + date_str, pubstmt_str):
                            newItem['collection-number'] = re.sub(volume_str + '[\.,]? ' + place_str + ': ' + publisher_str + ', ' + date_str, r'\1', pubstmt_str).strip()
                            newItem['publisher-place'] = re.sub(volume_str + '[\.,]? ' + place_str + ': ' + publisher_str + ', ' + date_str, r'\2', pubstmt_str)
                            newItem['publisher'] = re.sub(volume_str + '[\.,]? ' + place_str + ': ' + publisher_str + ', ' + date_str, r'\3', pubstmt_str)
                        # All other patterns
                        else:
                            # print(pubstmt_str)
                            newItem['publisher'] = pubstmt_str

                    # Process book chapters
                    # TODO: parse and disaggregate where possible
                    elif newItem['type'] == 'chapter':
                        newItem['publisher'] = pubstmt_str

                    else:
                        msg = f'WARNING: Unrecognized CSL type for transform of {sourceItem["@xml:id"]}.'
                        print(msg)
                        warning_log.append(msg)

                    # Reprints

                    # NOTE: the CSL spec accommodates earlier publications, not later ones.
                    # The presumption is that one cites the later publication, with notice
                    # of the original/earlier publication date.

                    # To preserve both dates, I map the 'repr.' date to `issued` and
                    # reassign the original `issued` values to `original-date`. In some
                    # cases this will create a bad reference, mixing original and later
                    # publisher names, places
                    #
                    # NOTE: This should be rethought

                    pattern = '\(\d\d\d\d\), repr. \d\d\d\d'
                    regexMatch = re.search(pattern, pubstmt_str)
                    if regexMatch:
                        newItem['original-date'] = {'date-parts': dateList.copy() } # copy and reassign
                        dateList.clear()
                        year = re.sub('^.*repr. (\d\d\d\d).*$', r'\1', pubstmt_str)
                        year = int(year)
                        dateList = format_dates(year, dateList)
                        dateObject = {'date-parts': dateList}
                        newItem['issued'] = dateObject

    return newItem, warning_log

def process_ref(title):
    if '#text' in title['ref']:
        this_book_title = format_string(title['ref'].pop('#text'))
    if title['ref'].get('@type', '') == 'url':
        if title['ref'].get('@n', '') != '':
            url = title['ref'].pop('@n')
            title['ref'].pop('@type')
    return this_book_title, url

def format_dates(year, dateList):
    year = int(year)
    dateParts = []
    dateParts.append(year)
    dateList.append(dateParts)
    return dateList

def uncollapse_date_ranges(dateValue, dateList):
    range_patterns = \
        [
            ('^\d\d\d\d-\d$', '^(\d\d\d\d)-\d$', '^(\d\d\d)\d-(\d)$'),
            ('^\d\d\d\d-\d\d$', '^(\d\d\d\d)-\d\d$', '^(\d\d)\d\d-(\d\d)$'),
            ('^\d\d\d\d-\d\d\d\d$', '^(\d\d\d\d)-\d\d\d\d$', '^\d\d\d\d-(\d\d)(\d\d)$')
        ]
    for idx in range(len(range_patterns)):
        pattern = range_patterns[idx][0]
        regexMatch = re.search(pattern, dateValue)
        if regexMatch:
            year = re.sub(range_patterns[idx][1], r'\1', dateValue)
            dateList = format_dates(year, dateList)
            year = re.sub(range_patterns[idx][2], r'\1\2', dateValue)
            dateList = format_dates(year, dateList)
            return dateList

def format_theses(newItem, string):
    if 'Diss.' in string:
        newItem['type'] = 'thesis'
        newItem['genre'] = 'Ph.D. diss.'
        string = re.sub('Diss\. ', '', string)

    else: # 'thesis', two items only
        newItem['type'] = 'thesis'
        newItem['genre'] = 'M.A. thesis'
        string = re.sub('MA thesis\. ', '', string)
        string = re.sub('M\.Litt thesis\. ', '', string)

    string = re.sub(', \d\d\d\d', '', string)
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
    output_filename = destination + 'bibliography.yaml'
    yaml_dump = yaml.dump(conversion, sort_keys=False, allow_unicode=True)
    with open(output_filename, 'w') as file:
        file.write(yaml_dump)
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
