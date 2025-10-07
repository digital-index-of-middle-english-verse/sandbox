# This script walks a transect through item records in Records.xml, from the
# top level down to witness keys. Unexpected data types and structures are
# reported. (These warnings are less important, now that the XML file is
# validated by schema.)

# Selected fields are extracted into a new dictionary for further analysis.
# Counts are produced of (1) documentary witnesses bearing each verse item; (2)
# verse items in each documentary witness; (3) verse items with no recorded
# edition (i.e., as yet unprinted).

# Results are written to the `artefacts/` directory.

import os
import xmltodict
import re

source = '../../dimev/data/Records.xml'
dest_dir = '../artefacts/'
log_file = 'warnings.txt'
summary_output = 'summary-analysis-of-Records.md'

def read_xml_to_string(source):
    print(f'Reading source file `{source}` to string...')
    with open(source) as f:
        xml_string = f.read()
    print('Preprocessing string...')
    xml_string = re.sub(' {2,}', ' ', xml_string) # remove whitespace
    xml_string = re.sub('\\n', '', xml_string) # remove newlines
    xml_string = re.sub('<lb/>', '\\n    ', xml_string) # replace <lb/> elements with newlines and spaced indent
    xml_string = re.sub('<sup>', 'BEGIN_SUP', xml_string) # replace <sup> tags
    xml_string = re.sub('</sup>', 'END_SUP', xml_string)
    xml_string = re.sub('<i>', 'BEGIN_ITALICS', xml_string)  # replace <i> tags
    xml_string = re.sub('</i>', 'END_ITALICS', xml_string)
    xml_string = re.sub(r'<ref xml:target="([\.0-9]+)" *>[0-9]+</ref>', 'DIMEV_' + r'\1', xml_string)
    # xml_string = re.sub(r'<mss key="([A-Za-z0-9]+)"/>', 'MS_' + r'\1', xml_string) # This substitution disrupts rendering of <ghost>
    return xml_string

def xml_to_dict(xml_string):
    print('Parsing string as a Python dictionary...\n')
    xml_dict = xmltodict.parse(xml_string)
    items = xml_dict['records']['record'] # strip outer keys
    return items

def warn(msg, dimevID):
    msg = 'WARNING: ' + msg
    warning_log.append(msg)

def get_valid_input(prompt, options):
    while True:
        choice = input(prompt).lower()
        if choice in options:
            return choice
        prompt = "Invalid selection. Try again. "

def create_ms_index(wit_id, dimev_id, document_contents):
    if wit_id in document_contents.keys():
        item_list = document_contents[wit_id]
        item_list.append(dimev_id)
        document_contents[wit_id] = item_list
    else:
        document_contents[wit_id] = [dimev_id]
    return document_contents

def calc_percent(fraction, total):
    percent = 100 * fraction / total
    percent = str(round(percent, 1)) + '%'
    return percent

def strip_italics(string):
    if type(string) == str:
        string = re.sub('BEGIN_ITALICS', '', string)
        string = re.sub('END_ITALICS', '', string)
    return string

def get_editions(dimevID, witness):
    editions = False
    if 'editions' in witness:
        editions = True
    return editions

# read the source file to string and pre-process
xml_string = read_xml_to_string(source)

# create a dictionary
items = xml_to_dict(xml_string)

# create empty counters and containers
## data errors
item_not_dict = 0
missing_witnesses = 0
witnesses_not_dict = 0
witnesses_without_child = 0

## valid item types
no_id = 0
child_is_dict = 0
child_is_list = 0

## collection containers
warning_log = ['Warnings from the latest run of `inspect-Records.py`.']
markdown = []
document_contents = {} # a "Manuscript Index" to DIMEV, expressed as dict (for each key-value pair, the key is a source identifier, the value is a list of items in that source)
item_records = [] # a selective record of DIMEV items

## total hits (all witnesses of all valid items)
checks = 0

for idx in range(len(items)):
    item = items[idx]
    if type(item) != dict:
        msg = 'Unexpected data type. <record> is not a dictionary'
        warn(msg, '')
        item_not_dict += 1
    else:
        if '@xml:id' not in item:
            no_id += 1
        else:
            dimevID = item['@xml:id']

            # extract witness keys
            if 'witnesses' not in item:
                msg = f'Unexpected data structure. {dimevID} has no element <witnesses>.'
                warn(msg, dimevID)
                missing_witnesses += 1
            else:
                if type(item['witnesses']) != dict:
                    msg = f'Unexpected data type. The element <witnesses> in {dimevID} is not a dictionary.'
                    warn(msg, dimevID)
                    witnesses_not_dict += 1
                else:
                    if 'witness' not in item['witnesses']:
                        msg = f'Unexpected data structure. The element <witnesses> in {dimevID} has no child <witness>.'
                        warn(msg, dimevID)
                        witnesses_without_child += 1
                    else:
                        witnesses = item['witnesses']['witness']
                        extracted_item = {'id': dimevID}
                        if type(witnesses) == dict:
                            child_is_dict += 1
                            wit_id = witnesses['source']['@key']
                            document_contents = create_ms_index(wit_id, dimevID, document_contents)
                            extracted_item['witnesses'] = [wit_id]
                            extracted_item['editions'] = get_editions(dimevID, witnesses)
                            if 'allLines' in witnesses.keys():
                                extracted_item['editions'] = True # NOTE: Treat single-witness items, fully transcribed by DIMED, as 'edited'
                            checks += 1
                        else:
                            if type(witnesses) == list:
                                child_is_list += 1
                                wit_list = []
                                ed_dict = {}
                                for idx in range(len(witnesses)):
                                    wit_id = witnesses[idx]['source']['@key']
                                    document_contents = create_ms_index(wit_id, dimevID, document_contents)
                                    wit_list.append(wit_id)
                                    ed_dict[wit_id] = get_editions(dimevID, witnesses[idx])
                                    checks += 1
                                extracted_item['witnesses'] = wit_list
                                extracted_item['editions'] = any(ed_dict.values())
                        item_records.append(extracted_item)

unedited_items = []
for item in item_records:
    if not item['editions']:
        item_id = re.sub('record-', '', item['id'])
        unedited_items.append(item_id)
unedited_items.sort(key=float)

# Write summary of counts
markdown.append('# Summary of walk')

## Gather raw counts
report_parts = [ \
    'Total items found: ' + str(len(items)),
    'Items of type dictionary without `@xml:id` (these are presumed cross-references): ' + str(no_id),
    'Items with xml:id but no element `witnesses` (these are also presumed cross-refs): ' + str(missing_witnesses),
    'Items with child-element `witness` of type dictionary: ' + str(child_is_dict),
    'Items with child-element `witness` of type list: ' + str(child_is_list),
    'Items with no recorded edition: ' + str(len(unedited_items)),
    'Total unique item-instances (excluding data errors): ' + str(checks),
    'Total source keys: ' + str(len(document_contents))
    ]

## Format raw counts
markdown.append('## Raw counts')
n = 1
for line in report_parts:
    prefix = str(n) + '. '
    markdown.append(prefix + line)
    n += 1
report_parts.clear()

## Gather interpreted counts
data_errors = item_not_dict + missing_witnesses + witnesses_not_dict
valid_items = child_is_dict + child_is_list
report_parts = [ \
    'Total valid items, excluding cross-references: ' + str(valid_items)
    ]

## Format interpreted counts
markdown.append('\n## Interpretation')
for line in report_parts:
    prefix = str(n) + '. '
    markdown.append(prefix + line)
    n += 1

## Check sums
check = len(items) - data_errors - no_id == valid_items
if not check:
    msg = 'Unknown data error. Counts do not add up.'
    warn(msg, '')

## Get input
prompt = 'Print summary counts to terminal? (y/N) '
options = ['y', 'n', '']
job = get_valid_input(prompt, options)
if job == 'y':
    for line in markdown:
        print(line)

# Prepare distributional data (items with n witnesses and vice versa)
print('\nPreparing distributional data...')
item_counts = []
for idx in document_contents:
    item_counts.append(len(document_contents[idx]))
max_item_count = max(item_counts)
n_items = list(range(1, max_item_count + 1))

witnesses_with_n_items = []
for n in n_items:
    count = 0
    for key in document_contents.keys():
        if len(document_contents[key]) == n:
            count += 1
    witnesses_with_n_items.append(count)


witness_counts = []
for item in item_records:
    witness_counts.append(len(item['witnesses']))
max_wit_count = max(witness_counts)
n_witnesses = list(range(1, max_wit_count + 1))

items_with_n_witnesses = []
for n in n_witnesses:
    count = 0
    for item in item_records:
        if len(item['witnesses']) == n:
            count += 1
    items_with_n_witnesses.append(count)

total_witnesses = len(document_contents)
total_items = len(item_records)

## Calculate and report summaries for items
markdown.extend(['', '# Summary counts for items', '## Largest fractions'])

### Largest fractions

for idx in range(3):
    msg = '- ' + str(items_with_n_witnesses[idx]) + ' items (' + calc_percent(items_with_n_witnesses[idx], total_items) + ') have ' + str(idx+1) + ' witness/es'
    markdown.append(msg)

### Upper percentiles
markdown.extend(['', '## Upper percentiles'])
threshold_ratios = [.90, .95, .99]

for ratio in threshold_ratios:
    count = 0
    for idx in range(len(items_with_n_witnesses)):
        count += items_with_n_witnesses[idx]
        if count / total_items > ratio:
            msg = '- ' + str(int(100 * ratio)) + '% of items have ' + str(n_witnesses[idx-1]) + ' or fewer witnesses'
            markdown.append(msg)
            break

### Highest counts
witness_counts.sort()
markdown.extend(['', '## Items with highest numbers of witnesses'])
n = 0
count_list = []
while n < 5:
    count = witness_counts.pop(-1)
    if count not in count_list:
        count_list.append(count)
    n += 1
hit_list = []
for count in count_list:
    for item in item_records:
        if len(item['witnesses']) == count:
            hit_list.append(item['id'])
for dimevID in hit_list:
    for idx in range(len(items)):
        item = items[idx]
        if type(item) == dict and '@xml:id' in item.keys():
            if item['@xml:id'] == dimevID:
                if 'titles' in item.keys():
                    title = item['titles']['title']
                    if type(title) == list:
                        title = title[0]
                if type(title) == str:
                    title = strip_italics(title)
    for item in item_records:
        if item['id'] == dimevID:
            witness_count = len(item['witnesses'])
    msg = '- ' + title + ' (' + dimevID + '): ' + str(witness_count)
    markdown.append(msg)

## Calculate and report summaries for witnesses
### Largest fractions
markdown.extend(['', '# Summary counts for witnesses', '## Largest fractions'])

for idx in range(3):
    msg = '- ' + str(witnesses_with_n_items[idx]) + ' witnesses (' + calc_percent(witnesses_with_n_items[idx], total_witnesses) + ') have ' + str(idx+1) + ' item/s'
    markdown.append(msg)

### Upper percentiles
markdown.extend(['', '## Upper percentiles'])
threshold_ratios = [.85, .90, .95, .99]

for ratio in threshold_ratios:
    count = 0
    for idx in range(len(witnesses_with_n_items)):
        count += witnesses_with_n_items[idx]
        if count / total_witnesses > ratio:
            msg = '- ' + str(int(100 * ratio)) + '% of witnesses have ' + str(n_items[idx-1]) + ' or fewer items'
            markdown.append(msg)
            break

### Highest counts
item_counts.sort()
markdown.extend(['', '## Witness keys with highest numbers of items'])
n = 0
while n < 5:
    count = item_counts.pop(-1)
    for key in document_contents.keys():
        if len(document_contents[key]) == count:
            itemID = key
            break
    msg = '- ' + itemID + ': ' + str(count)
    markdown.append(msg)
    n += 1

# Unprinted items

markdown.extend(['', '# Verse items with no recorded edition', 'References are to DIMEV numbers.', 'This list excludes verse items transmitted in a single witness, transcribed in full in the DIMEV data element "allLines".', ''])
for item in unedited_items:
    markdown.append(f'- {item}')

# Write artefacts
print(f'Writing output to `{dest_dir}`.')
with open(dest_dir + log_file, 'w') as file:
    for line in warning_log:
        file.write(line + '\n')
print(f'Wrote log of warnings to `{log_file}`.')

markdown.insert(0, 'This file is written by `inspect-Records.py`.\n')
with open(dest_dir + summary_output, 'w') as file:
    for line in markdown:
        file.write(line + '\n')
print(f'Wrote analysis of distributions to `{summary_output}`.')

print('Goodbye')
