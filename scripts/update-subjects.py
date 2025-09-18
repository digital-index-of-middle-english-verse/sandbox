# This Python script reads subject terms from the WIP crosswalk
# (`subjects.csv`), reports added and deleted subject terms, and merges the
# changed subject terms into another WIP file, in which we assign subject terms
# to categories (`subject-categories.csv`).

import os
import csv

# Root variables

data_dir = '../artefacts/'
csv_sources = ['subjects.csv', 'subject-categories.csv']

def verify_path(csv_sources, data_dir):
    print('Verifying presence of data files...')
    exceptions = 0
    for file in csv_sources:
        file_path = data_dir + file
        if not os.path.exists(file_path):
            print(f"Source file {file} not found on path {data_dir}.")
            exit()
    print('Success')

def load_csv_to_dict(csv_sources, data_dir):
    subject_crosswalk = []
    subject_categories = []
    destination_list = [subject_crosswalk, subject_categories]
    n = 0
    while n < len(destination_list):
        file_path = data_dir + csv_sources[n]
        destination = destination_list[n]
        with open(file_path, 'r') as file:
            reader = csv.DictReader(file)
            for row in reader:
                destination.append(row)
        n += 1
    return subject_crosswalk, subject_categories

def process_subject_terms(subject_crosswalk):
    revised_subjects = set()
    old_subjects = set()
    deleted_subjects = set()
    for item in subject_crosswalk:
        old_subjects.add(item['subject'])
        if item['new subjects'] == '':
            revised_subjects.add(item['subject'])
        elif item['new subjects'] == 'DELETE':
            deleted_subjects.add(item['subject'])
        else:
            new_subject_list = item['new subjects'].split("; ")
            for subject_term in new_subject_list:
                revised_subjects.add(subject_term)
    added_subjects = set()
    for subject_term in revised_subjects:
        if subject_term not in old_subjects:
            added_subjects.add(subject_term)
    added_subjects = list(added_subjects)
    added_subjects.sort()
    deleted_subjects = list(deleted_subjects)
    deleted_subjects.sort()
    print(f'\nFound {str(len(subject_crosswalk))} subject terms in DIMEV 1.0')
    print(f'Of these, {str(len(deleted_subjects))} are marked for deletion')
    print(f'{str(len(added_subjects))} new subject terms will be added, for a total of {str(len(revised_subjects))} subject terms after revision')
    print(f'\nThe deleted subject terms:\n{"; ".join(deleted_subjects)}')
    print(f'\nThe new subject terms:\n{"; ".join(added_subjects)}')
    return revised_subjects

def create_subject_categories(revised_subjects, subject_categories):
    revised_subject_categories = []
    revised_subjects = list(revised_subjects)
    revised_subjects.sort()
    for subject_term in revised_subjects:
        revised_subject_categories.append({'subject': subject_term, 'category': ''})
    for base_item in revised_subject_categories:
        for content_item in subject_categories:
            if content_item['subject'] == base_item['subject']:
                base_item['category'] = content_item['category']
    category_terms = set()
    unassigned_subject_terms = 0
    for item in revised_subject_categories:
        if item['category'] == '':
            unassigned_subject_terms += 1
        else:
            category_terms.add(item['category'])
    category_terms = list(category_terms)
    category_terms.sort()
    print(f'\nFound {str(len(category_terms))} subject categories: {", ".join(category_terms)}')
    print(f'Found {str(unassigned_subject_terms)} subject terms unassigned to a category')
    return revised_subject_categories

def write_subject_categories(revised_categories):
    destination = data_dir + csv_sources[1]
    with open(destination, 'w') as file:
        file.write('subject,category\n')
        for item in revised_categories:
            if ',' in item['subject']:
                file.write('"' + item['subject'] + '",' + item['category'] + '\n')
            else:
                file.write(item['subject'] + ',' + item['category'] + '\n')
    print(f'\nWrote {str(len(revised_categories))} lines of data to {destination}')

verify_path(csv_sources, data_dir)
subject_crosswalk, subject_categories = load_csv_to_dict(csv_sources, data_dir)
revised_subjects = process_subject_terms(subject_crosswalk)
revised_categories = create_subject_categories(revised_subjects, subject_categories)
write_subject_categories(revised_categories)
print('Done')
