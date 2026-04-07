import os
from lxml import etree
import re

# top-level variables

src_dir = '../../dimev/data/'
source_file = 'Manuscripts.xml'
bibliography_file = 'Bibliography.xml'
namespace = '{http://www.w3.org/XML/1998/namespace}'

def main():
    tree = etree.parse(src_dir + source_file)
    root = tree.getroot()

    # Add facsimiles
    root = add_facsimile_urls(root)

    print('All transformations complete')
    etree.indent(tree, space="    ", level=0)
    tree.write(src_dir + source_file, pretty_print=True, xml_declaration=True, encoding='UTF-8')
    print(f'Wrote the updated tree to {source_file}')

def add_facsimile_urls(root):
    facs_list = extract_keys_and_urls(src_dir + bibliography_file)
    unmatched_ids = []
    facs_count = 0
    for ref_pair in facs_list:
        # Check for a matching xml:id in Manuscripts.xml
        match = False
        for item in root.findall('item'):
            ms_id = item.get(namespace + 'id')
            if ref_pair[0] == ms_id:
                item, facs_count = add_surrogates_el(item, ref_pair[1], facs_count)
                match = True
                break
        if match == False:
            unmatched_ids.append(ref_pair[0])
    print(f'\nAdded {facs_count} facsimiles to Manuscripts.xml')
    if len(unmatched_ids) > 0:
        print(f'Found {len(unmatched_ids)} bibliography keys without matching manuscript id: {", ".join(unmatched_ids)}')

def add_surrogates_el(item, url, facs_count):
    surrogates = item.find('surrogates')
    if surrogates is None:
        surrogates = etree.Element('surrogates')
        ref = etree.Element('ref', target=url)
        surrogates.append(ref)
        if item.find('lang') is None:
            item.insert(3, surrogates)
        else:
            item.insert(4, surrogates)
        facs_count += 1
    else:
        url_list = []
        refs = surrogates.findall('ref')
        for ref in refs:
            url_list.append(ref.get('target'))
        if url not in url_list:
            ref = etree.Element('ref', target=url)
            surrogates.append(ref)
            facs_count += 1
    return item, facs_count

def extract_keys_and_urls(file):

    # Some on-line facsimiles recorded in Bibliography.xml are of manuscripts
    # unrecorded in Manuscripts.xml. These facsimiles are referenced nowhere in
    # DIMEV data and should be excluded from the present transformation.

    unused_ids = [
            'Chetham6680',
            'Chetham27938',
            'Chetham27911',
            'Chetham6723',
            'Chetham6711'
            ]

    # Check Bibliography.xml directly
    print('Building the list of on-line facsimiles...')

    facs_list = [] # Create a container for a list of key-url tuples
    bib_tree = etree.parse(file)
    bib_root = bib_tree.getroot()
    url_checks = 0
    for item in bib_root.findall('bibl'):
        bib_key = item.get(namespace + 'id')

        # Identify online facsimiles (these should have a URL as text content
        # of the pubstmt element). Extract the URL from pubstmnt, if present.

        pubstmt = item.find('pubstmt')
        pubstmt_text = etree.tostring(pubstmt, encoding='unicode', method='text')
        if 'http' in pubstmt_text and bib_key not in unused_ids:
            url_from_pubstmt = re.sub(r'^\d\d\d\d;?\W*', '', pubstmt_text).strip()
            bib_key = preprocess_bibkey(bib_key)
            ref_pair = (bib_key, url_from_pubstmt)
            facs_list.append(ref_pair)

            # Facsimiles have an identical URL within the titlestmt block.
            # Check for that and verify that the URLs are indeed identical
            url_checks = cross_check_facs_urls(item, url_from_pubstmt, url_checks)

    print(f'Found {len(facs_list)} digital facsimiles, excluding {len(unused_ids)} digital facsimiles of manuscripts unreferenced elsewhere in DIMEV files')
    print(f'Cross-checked {url_checks} URLs')
    cross_check_facs_sets(facs_list, unused_ids)
    return facs_list

def cross_check_facs_sets(facs_list, unused_ids):

    print('Checking the list against a previous one, created with different logic by the script transform-Bibl.py...')

    # Begin with xml:id values of items identified as on-line facsimiles in
    # transform-Bibl.py. The logic used to identify these facsimiles is
    # questionable, but it serves as a check on the logic used below, in this
    # present function

    facs_keys_from_transformBibl = {'Bodmer48', 'BritLib2014', 'Balliol354', 'Lydgate1451', 'Parker2008', 'Sumer', 'BLRoy18dii', 'BLHar2946', 'BLAru57', 'NatLibMed514', 'BLCottCalaix', 'BLCottJulDIX', 'BLHar24', 'BLHar3943', 'BLAru285', 'BLEge2711', 'BLHar525', 'BLHar565', 'BLHar682', 'BLHar941', 'BLHar1121', 'BLHar1245', 'BLHar1706', 'BLHar1770', 'BLHar2280', 'BLHar2320', 'BLHar2338', 'BLHar2392', 'BLHar3954', 'BLHar4912', 'BLHar2277', 'BLHar2278', 'BLHar2376', 'BLHar3776', 'BLHar3860', 'BLHar3869', 'BLHar5272', 'BLHar1735', 'BLAdd31922', 'BLLan204', 'BLLan762', 'BLRoy12Cxii', 'BLRoy12Fxiii', 'BLRoy17Ai', 'BLRoy17Dvi', 'LOCMS4', 'NLWPork10', 'CamTCC301', 'CamTCC305', 'CamTCC335', 'CamTCC181', 'CamTCC1037', 'CamTCC605', 'CamTCC599', 'CamTCC323', 'CamTCC731', 'CamTCC759', 'CamTCC905', 'CamTCC1413', 'CamTCC1486', 'TCCFragment', 'Lam260', 'Lam306', 'YaleBei661', 'YaleBei1222', 'TokyoTak4', 'TokyoTak6', 'TokyoTak12', 'TokyoTak15', 'TokyoTak17', 'TokyoTak18', 'TokyoTak22', 'TokyoTak23', 'TokyoTak24', 'TokyoTak29', 'TokyoTak30', 'TokyoTak32', 'TokyoTak33', 'TokyoTak35', 'TokyoTak40', 'TokyoTak46', 'TokyoTak51', 'TokyoTak52', 'TokyoTak54', 'TokyoTak61', 'TokyoTak64', 'TokyoTak65', 'TokyoTak66', 'TokyoTak67', 'TokyoTak78', 'TokyoTak79', 'TokyoTak94', 'TokyoTak96', 'TokyoTak97', 'TokyoTak98', 'TokyoTak112', 'Austin46', 'Austin143', 'BodBar20', 'Bod414', 'Bod686', 'BodDoud4', 'BodHatDon1', 'BodRawPoe141', 'BodRawPoe223', 'BodRawD913', 'BodArcSelB14', 'OxfCCC198', 'BodJunius1', 'Wellcome225', 'Wellcome406', 'Wellcome542', 'Wellcome692', 'Wellcome693', 'Wellcome5650', 'CamCCC7', 'CamCCC167', 'CamCCC354', 'CamCCC357', 'Chetham6680', 'ChethamE610', 'Chetham6690', 'Chetham27938', 'Chetham27911', 'Chetham11379', 'Chetham8009', 'Chetham6723', 'Chetham6711', 'Chetham6709', 'OxfStJohn56', 'OxfStJohn57', 'OxfStJohn94', 'OxfStJohn340'}

    print(f'The script transform-Bibl.py identified {len(facs_keys_from_transformBibl)} on-line facsimiles.')

    processed_facs_keys_from_transformBibl = set()
    for bib_key in facs_keys_from_transformBibl:
        if bib_key not in unused_ids:
            bib_key = preprocess_bibkey(bib_key)
            processed_facs_keys_from_transformBibl.add(bib_key)

    print(f'Of these, {len(facs_keys_from_transformBibl) - len(processed_facs_keys_from_transformBibl)} are unreferenced in other DIMEV files.')

    # check the new list against the previous one
    new_set_of_keys = set()
    for pair in facs_list:
        new_set_of_keys.add(pair[0])
    if new_set_of_keys == processed_facs_keys_from_transformBibl:
        print('The new and old logics yield identical sets of on-line facsimiles.')
    else:
        print('WARNING: The lists of on-line facsimiles differ.')
    print('Proceeding with the new list...')

def preprocess_bibkey(bib_key):

    # On-line facsimiles whose xml:id does not match the xml:id of the
    # corresponding item in Manuscripts.xml.

    manual_matches = [
            ('BritLib2014', 'BLAdd22283'),
            ('Balliol354', 'OxfBal354'),
            ('Lydgate1451', 'HarEng752'),
            ('Parker2008', 'OxfCCC61'),
            ('Sumer', 'BLHar978'),
            ('BLRoy18dii', 'BLRoy18Dii'),
            ('BLCottCalaix', 'BLCottCalAIX'),
            ('LOCMS4', 'LibCong4')
            ]

    # Use the xml:id in Manuscripts.xml (index 1)
    for keypair in manual_matches:
        if keypair[0] == bib_key:
            bib_key = keypair[1]
            break
    return bib_key

def cross_check_facs_urls(item, url_from_pubstmt, url_checks):
    # Walk the titlestmt tree and extract the URL, if present.
    titlestmt = item.find('titlestmt')
    title = titlestmt.find('title')
    ref = title.find('ref')
    if ref is not None:
        url_from_titlestmt = ref.get('n')
        # Check that URLs are identical
        url_checks += 1
        if url_from_titlestmt != url_from_pubstmt:
            print(f'URL values differ:\n{url_from_titlestmt}\n{url_from_pubstmt}')
    return url_checks

def unify_files(root):
    print('Reconciling Manuscripts.xml and MSSIndex.xml')
    tree2 = etree.parse(src_dir + mssindex_xml)
    root2 = tree2.getroot()
    count_new = 0
    for location in root2:
        loc_val2 = location.get('key')
        for repository in location:
            repo_val2 = repository.get('key')
            for item2 in repository:
                if item2.get(namespace + 'id') is not None:
                    root, count_new = write_to_root(root, item2, loc_val2, repo_val2, count_new)
    print(f'Wrote {count_new} items to Manuscripts.xml')
    return root

def write_to_root(root, item2, loc2_val, repo2_val, count_new):
    itemID2 = item2.get(namespace + 'id')
    shelfmark2 = item2.find('desc')
    lang2 = item2.find('lang')
    item_id_found = False
    for item in root:
        itemID1 = item.get(namespace + 'id')
        if itemID1 == itemID2:
            # remove current child elements
            for child in item:
                item.remove(child)
            # create new child elements
            loc_el = etree.Element('loc')
            loc_el.text = loc2_val
            repo_el = etree.Element('repos')
            repo_el.text = repo2_val
            # insert new elements
            item.insert(0, loc_el)
            item.insert(1, repo_el)
            item.insert(2, shelfmark2)
            if lang2 is not None:
                item.insert(3, lang2)
            item_id_found = True
            break
    if item_id_found == False:
        loc_el = etree.Element('loc')
        loc_el.text = loc2_val
        item2.insert(0, loc_el)
        repo_el = etree.Element('repos')
        repo_el.text = repo2_val
        item2.insert(1, repo_el)
        count_el = item2.find('count')
        item2.remove(count_el)
        root.append(item2)
        count_new += 1
    return root, count_new

main()
