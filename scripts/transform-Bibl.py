# This script attempts to transform Bibliography.xml into valid CSL data.
# Complex transformations are tested by round-tripping. The pop() method is
# used to delete source values successfully converted; warnings are thrown for
# source items with left-over unconsumed values.
#
# The translation validates successfully against the CSL schema but it is lossy
# and buggy. Just half of items pass the round-tripping test. The rest (~1500)
# generate a warning of some kind. This mass of warnings is sorted as follows:
#
# - Warnings pertaining to date values or to basic data structure or data type
# are printed to the terminal and written to the log file. There are about 60
# of these.
#
# - The rest (the vast majority) are just written to the log file
#
# Any validation error emitted by jsonschema is written to the end of log file,
# after warnings thrown during conversion
#
# TODO: improve processing, disaggregation of `pubstmt` (a nasty free text
# field in the source XML)
#
# TODO: fix translation of nested titles (inner elements are dropped in the
# current translation). See e.g. Albrecht1954a
#
# TODO: translate urls (for online editions and digital facsimiles, described
# in the DIMEV editing manual)
#
# TODO: handle cross-references (items without @xml:id)

import os
import xmltodict
import re
import yaml
import json
import jsonschema

# Top-level variables
source = '../DIMEV_XML/Bibliography.xml'
destination = '../artefacts/'
csl_schema = '../schemas/csl-data.json'
# test_sample= range(50)
warning_log = ['Warnings from the latest run of `transform-Bibl.py`.\n']
count_warnings = 0
count_items_without_id = 0
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

def convert_item(sourceItem, count_warnings, warning_log):
    if 'index' in sourceItem:
        sourceItem.pop('index') # NOTE: Ignore keywords, for now
    newItem = {}
    newItem['id'] = sourceItem.get('@xml:id')
    newItem['type'] = 'book' # set a default value for a required field
    if 'authorstmt' in sourceItem:
        authorstmt = sourceItem['authorstmt']
        if authorstmt is not None:
            for agent in ['author', 'editor']:
                if agent in authorstmt:
                    newItem[agent] = convert_agents(authorstmt[agent], sourceItem['@xml:id'])
                    if len(authorstmt[agent]) == 0:
                        authorstmt.pop(agent)
            if len(authorstmt) == 0:
                sourceItem.pop('authorstmt')
    if 'titlestmt' in sourceItem:
        if sourceItem['titlestmt'] is None:
            msg = f'WARNING: Empty `titlestmt` in item {sourceItem["@xml:id"]}.'
            print(msg)
            warning_log.append(msg)
        else:
            titlestmt = sourceItem['titlestmt']['title']
            if type(titlestmt) == dict:
                titlestmt = [titlestmt]
            for title in titlestmt:
                # NOTE: "a"=Article markup "m" =Monograph "j" =Journal "r" =Review "s" =Series
                # TODO: accommodate 'r'
                # TODO: assign other CSL item types
                if type(title) != dict:
                    msg = f'WARNING: Unexpected data type for `title` element in item {sourceItem["@xml:id"]}.'
                    print(msg)
                    warning_log.append(msg)
                else:
                    if title['@level'] == 'j':
                        newItem['type'] = 'article-journal'
                        newItem['container-title'] = title.pop('#text')
                    if title['@level'] == 's':
                        newItem['type'] = 'book'
                        newItem['collection-title'] = title.pop('#text')
                    if title['@level'] == 'a' or title['@level'] == 'm':
                        if '#text' in title:
                            newItem['title'] = title.pop('#text')
                    # clean up
                    if len(title) == 1 and '@level' in title.keys():
                        title.pop('@level')
            sourceItem.pop('titlestmt')

    if 'pubstmt' in sourceItem:
        pubstmt = sourceItem['pubstmt']
        if pubstmt is None:
            msg = f'WARNING: Empty `pubstmt` in item {sourceItem["@xml:id"]}.'
            print(msg)
            warning_log.append(msg)
        elif type(pubstmt) is not dict:
            msg = f'WARNING: Unexpected data type for `pubstmt` in item {sourceItem["@xml:id"]}.'
            print(msg)
            warning_log.append(msg)
        else:
            # First, try to extract a four-digit publication year from the '@date' attribute
            # Conditions are necessary, as attribute values have date ranges and typos
            if '@date' not in pubstmt:
                msg = f'WARNING: No `@date` attribute in item {sourceItem["@xml:id"]}. Skipping.'
                print(msg)
                warning_log.append(msg)
            else:
                dateValue = pubstmt['@date']
                pattern = '[A-Za-z=\?\+]'
                regexMatch = re.search(pattern, dateValue)
                if regexMatch:
                    msg = f'WARNING: Invalid value found for `@date` attribute in item {sourceItem["@xml:id"]}. Skipping.'
                    print(msg)
                    warning_log.append(msg)
                elif re.search('\d{5,}', dateValue):
                    msg = f'WARNING: Invalid value found for `@date` attribute in item {sourceItem["@xml:id"]}. Skipping.'
                    print(msg)
                    warning_log.append(msg)
                elif len(dateValue) < 4:
                    msg = f'WARNING: Invalid value found for `@date` attribute in item {sourceItem["@xml:id"]}. Skipping.'
                    print(msg)
                    warning_log.append(msg)
                else:
                    dateValue = re.sub('\[|\]', '', dateValue) # NOTE: strip brackets, for now
                    # NOTE: I use the 'more structured' representation of dates permitted by the CSL spec.
                    dateList = []
                    pattern = '^\d\d\d\d$'
                    regexMatch = re.search(pattern, dateValue)
                    if regexMatch:
                        year = pubstmt.pop('@date')
                        dateList = format_dates(year, dateList)
                    elif '-' in dateValue:
                        dateList = uncollapse_date_ranges(dateValue, dateList)
                    else:
                        msg = 'WARNING: Unsupported date pattern in item {sourceItem["@xml:id"]}. Skipping.'
                        warning_log.append(msg)

                    dateObject = {'date-parts': dateList}
                    newItem['issued'] = dateObject

            # Next, process the `#text` element
            # NOTE: this is error-prone and inelegant
            if '#text' not in pubstmt:
                msg = f'WARNING: No text value for `pubstmt` in item {sourceItem["@xml:id"]}. Skipping.'
                print(msg)
                warning_log.append(msg)
            else:
                string = pubstmt['#text']
                regexMatch = re.search('\(\d\d\d\d\): ', string)
                if regexMatch:
                    volume = re.sub(' \(\d\d\d\d\): .*$', '', string)
                    newItem['volume'] = volume
                    page = re.sub('^.*\(\d\d\d\d\): ', '', string)
                    newItem['page'] = page
                    # round-trip: rebuild the `#text` element from extracted parts and pop `#text` if True
                    if 'issued' in newItem and newItem['issued']['date-parts']:
                        if string == volume + ' (' + str(newItem['issued']['date-parts'][0][0]) +'): ' + page:
                            sourceItem['pubstmt'].pop('#text')
                else:
                    regexMatch = re.search('^\d', string)
                    if regexMatch:
                        number = re.sub(' .*$', '', string)
                        newItem['collection-number'] = number
                regexMatch = re.search('^e\. ?s\. \d+', string)
                if regexMatch:
                    number = re.sub('(^e\. ?s\. \d+).*$', r'\1', string)
                    newItem['collection-number'] = number
                regexMatch = re.search('\w: \w', string)
                if regexMatch:
                    publisher = re.sub('.*: ([\w&\./ ]+),.+$', r'\1', string)
                    newItem['publisher'] = publisher
                    place = re.sub(':.*$', '', string)
                    place = re.sub('^.*\d\.? ', '', place)
                    newItem['publisher-place'] = place
                    # round-trip: rebuild the `#text` element from extracted parts and pop `#text` if True
                    if 'collection-number' in newItem and 'issued' in newItem and newItem['issued']['date-parts']:
                        if string == newItem['collection-number'] + ' ' + newItem['publisher-place'] + ': ' + newItem['publisher'] + ', ' + str(newItem['issued']['date-parts'][0][0]):
                            sourceItem['pubstmt'].pop('#text')
                    elif 'issued' in newItem and newItem['issued']['date-parts']:
                        if string == newItem['publisher-place'] + ': ' + newItem['publisher'] + ', ' + str(newItem['issued']['date-parts'][0][0]):
                            sourceItem['pubstmt'].pop('#text')

                # Reprints

                # NOTE: the CSL spec accommodates earlier publications, not later ones.
                # The presumption is that one cites the later publication, with notice
                # of the original/earlier publication date.

                # To preserve both dates, I map the 'repr.' date to `issued` and
                # reassign the original `issued` values to `original-date`. In some
                # cases this will create a bad reference, mixing original and later
                # publisher names, places

                pattern = '\(\d\d\d\d\), repr. \d\d\d\d'
                regexMatch = re.search(pattern, string)
                if regexMatch:
                    newItem['original-date'] = {'date-parts': dateList.copy() } # copy and reassign
                    dateList.clear()
                    year = re.sub('^.*repr. (\d\d\d\d).*$', r'\1', string)
                    year = int(year)
                    dateList = format_dates(year, dateList)
                    dateObject = {'date-parts': dateList}
                    newItem['issued'] = dateObject

                    # round-trip: rebuild the `#text` element from extracted parts and pop `#text` if True
                    if 'collection-number' in newItem.keys():
                        if string == newItem['collection-number'] + ' (' + str(newItem['original-date']['date-parts'][0][0]) + '), repr. ' + str(newItem['issued']['date-parts'][0][0]):
                            sourceItem['pubstmt'].pop('#text')
            if len(sourceItem['pubstmt']) == 0:
                sourceItem.pop('pubstmt')
            # cleanup
            for key in newItem.keys():
                if type(newItem[key]) == str:
                    newItem[key] = re.sub('\.$', '', newItem[key])
    # Check for remaining fields
    if len(sourceItem) > 1:
        warning_log.append(f'WARNING: unconsumed values in item {sourceItem["@xml:id"]}')
        warning_log.append(str(sourceItem) + '\n')
        count_warnings += 1
    return newItem, count_warnings, warning_log

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

def convert_agents(agents, itemID):
    if type(agents) == dict:
        agents = [agents]
    nameList = []
    for nomen in agents:
        nameParts = {}
        if type(nomen['last']) == list:
            msg = f'WARNING: Unexpected data structure in the `authorstmt` of {itemID}'
            print(msg)
            warning_log.append(msg)
        else:
            nameParts['family'] = nomen.pop('last', '')
        if 'first' in nomen and nomen['first'] is not None:
            nameParts['given'] = nomen.pop('first', '')
        nameList.append(nameParts)
    return nameList

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

# convert items with `@xml:id`
conversion = []
if not 'test_sample' in locals():
    test_sample = range(len(items)) # Convert all items, unless a test_sample is specified previously
for idx in test_sample:
    if '@xml:id' in items[idx]:
        newItem, count_warnings, warning_log = convert_item(items[idx], count_warnings, warning_log)
        conversion.append(newItem)
    else:
        count_items_without_id += 1

# Validate and write
validate_items(conversion)

msg = f'Conversions completed with {count_warnings} warnings and {count_items_without_id} unconverted cross-references.'
print(msg)
warning_log.append(msg)
with open(log_file, 'w') as file:
    for line in warning_log:
        file.write(line + '\n')

write_to_file(conversion)
