#!/usr/bin/env python3
import sys
import csv
import string
import pprint
from subprocess import call
import click
import logging
from datetime import datetime
import re

# puts field data to lower case
def lower_getter(field):
    def _getter(obj):
        return obj[field].lower()
    return _getter

# used like this
#list_of_dicts.sort(key=lower_getter(key_field)) 

def logger_init():
    log = logging.getLogger('csvcut')
    log.setLevel(logging.DEBUG) # level of logger itself
    c_handle = logging.StreamHandler() # console handler
    c_handle.setLevel(logging.WARNING) # level of the console handler
    # create formatters and add it to the handler
    c_form = logging.Formatter('%(levelname)-5s %(message)s')
    c_handle.setFormatter(c_form)
    log.addHandler(c_handle) # add the handler to logger
    return log

log=logger_init()
# change default help options
cont_set = dict(help_option_names=['-h', '--help'])

@click.command(context_settings=cont_set)
@click.argument('filename')
@click.option('--verbose', '-v', count=True, default=False,
    help="enable INFO (-v) or DEBUG (-vv) logging on console")
@click.option('--type', '-t', "format",
    type=click.Choice(['vb', 'pp']), default="vb",
    help="which type of CSV modification?",)
@click.option('--dry-run', '-n', is_flag=True, default=False,
    help="don't write CSV file, just print data on console")
def csv_slimify(filename, verbose, format, dry_run):
    """cuts away unused columns of banking CSV exports."""
    if verbose == 1:
        log.handlers[0].setLevel(logging.INFO) # set cli handler to INFO,
    elif verbose > 1:
        log.handlers[0].setLevel(logging.DEBUG) # or to DEBUG level

    if "/" in filename:
        filenamepath=filename.rsplit('/',1)[0]
        filenamefile=filename.rsplit('/',1)[1]
        filename=filenamepath+"/"+filenamefile
    print('\nUsing source file "{}"\n'.format(filename))

    # DEBUG dump 1st 200 bytes
    log.debug("1st 200 bytes...")
    log.debug(repr(open(filename, 'rb').read(200)))
    log.debug("\n")

    # Cleanup source file -> e.g replace NUL characters
    # Load whole file as bytes into var data.
    fi = open(filename, 'rb')
    data = fi.read()
    fi.close()
    # Replace stuff and overwrite file.
    fo = open(filename, 'wb')
    if format == "vb":
        data_cleaned_up = data.replace(b'\x00', b'')
    elif format == "pp":
        data_cleaned_up = data.replace(b'\x00', b'')
        data_cleaned_up = data_cleaned_up.replace(b'\xbb', b'')
        data_cleaned_up = data_cleaned_up.replace(b'\xef', b'')
        data_cleaned_up = data_cleaned_up.replace(b'\xbf', b'')
    fo.write(data_cleaned_up)
    fo.close()

    # Guess CSV dialect and open file context.
    encoding = "iso-8859-1" if format == "vb" else "utf-8"
    with open(filename, 'r', encoding=encoding) as csvfile:
        dialect = csv.Sniffer().sniff(
            csvfile.read(1024), delimiters=[',', ';']
        )
        log.info('Detected CSV dialect:')
        log.info('quotechar: {}'.format(dialect.quotechar))
        log.info('delimiter: {}'.format(dialect.delimiter))
        log.info('doublequote: {}\n'.format(dialect.doublequote))

        # Set back file handle to beginning of file.
        csvfile.seek(0)
        # Load contents into OrderedDict (Py3.6) or dict (Py3.8) object.
        csv_dict = csv.DictReader(csvfile, dialect=dialect)
        log.info("csv_dict type is {}".format(csv_dict))
        log.info('csv.DictReader found fields: \n{}\n'.format(csv_dict.fieldnames))

        # With debug logging enabled, show how the data actually look like:
        if logging.getLevelName(log.handlers[0].level) == 'DEBUG':
            print('\nThis is what the source data looks like:\n')
            for row in csv_dict:
                pp = pprint.PrettyPrinter(indent=4, depth=1)
                pp.pprint(row)
            print('\n\n')

        # The cols we want in the output.
        if format == "vb":
            output_fields = ['Umsatzzeit', 'Buchungsdatum', 'Valutadatum',
                             'Betrag', 'Buchungstext', 'Umsatztext']
        elif format == "pp":
            # interesting_original_fields = [
            #     'Date', 'Time', 'Name', 'Type', 'Currency', 'Gross', 'Fee',
            #     'Net', 'Balance', 'From Email Address', 'To Email Address',
            #     'Item Title', 'Town/City'
            # ]
            output_fields = ['Date', 'Time', 'Currency', 'Gross',
                             'Fee', 'Net', 'Balance', 'Description', 'DateTime']

        if format == "vb":
            # Format Umsatzzeit so we can use it for sorting and strip useless
            # spaces in Buchungstext. Currently this code is unused and we sort
            # via Valutadatum still, since it's the closest to reality.
            csv_dict_mod = []
            for idx, row in enumerate(csv_dict):
                # print('This is csv_dict idx, row: {}, {}\n'.format(idx, row))
                csv_dict_mod.append(row)
                for col, value in row.items():
                    if col == 'Umsatzzeit':
                        date_time = datetime.strptime(
                            value, '%Y-%m-%d-%H.%M.%S.%f'
                        ).strftime('%Y-%m-%d %H:%M:%S')
                        csv_dict_mod[idx][col] = date_time
                    if col == 'Umsatztext':
                        csv_dict_mod[idx][col] = re.sub(
                            '\s+', ' ', value
                        )
        elif format == "pp":
            csv_dict_mod = []
            for idx, row in enumerate(csv_dict):
                # print('This is csv_dict idx, row: {}, {}\n'.format(idx, row))
                # Empty string as a default for new_row items.
                new_row = {field: '' for field in output_fields}
                for col, value in row.items():
                    # Merge Date/Time, translate to standard format, then write
                    # to separate fields again. Date field must be first in
                    # original data!
                    if col == "Date":  
                        new_row['DateTime'] = "".join([new_row['DateTime'], value])
                    elif col == "Time":
                        datetime_merged = " ".join([new_row['DateTime'], value])
                        datetime_o = datetime.strptime(
                            datetime_merged, '%d/%m/%Y %H:%M:%S'
                        )
                        new_row['DateTime'] = datetime_o.strftime('%Y-%m-%d %H:%M:%S')
                        new_row['Date'] = datetime_o.strftime('%Y-%m-%d')
                        new_row['Time'] = datetime_o.strftime('%H:%M:%S')
                    # Keep currency related as-is.
                    elif col in ["Currency", "Gross", "Fee", "Net", "Balance"]:
                        new_row[col] = value
                    # Ignore timezone col.
                    elif col in ["Timezone"]:
                        continue
                    # Put all the rest into a Description col.
                    else:
                        if new_row['Description'] == "":
                            delim = ""  # No delimitier if still empty
                        else:
                            delim = " / "
                        # Only add non-empty fields. Make sure value is always
                        # handled as a string.
                        if value:
                            new_row['Description'] = delim.join(
                                [new_row['Description'], str(value)]
                            )
                csv_dict_mod.append(new_row)

        log.info("csv_dict_mod type is {}\n".format(type(csv_dict_mod)))

        # Sort the list. Actually sortedlist is a list of dicts.
        if format == "vb":
            sortedlist = sorted(csv_dict_mod, key=lambda foo: (foo['Valutadatum'].lower()), reverse=False)
        elif format == "pp":
            sortedlist = sorted(csv_dict_mod, key=lambda foo: (foo['DateTime'].lower()), reverse=False)

        # log.info("sortedlist type is {} and contains {}\n".format(
        #     type(sortedlist), type(sortedlist[0])
        # ))

        # On dry-runs we only output what would be written to csv and exit.
        if dry_run:
            for row in sortedlist:
                row_str = ''
                for item in row.items():
                    row_str+= '| {} '.format(item[1])
                print('{}\n'.format(row_str))
            print("FIXME: Above fields are in the wrong order, this is what "
                  "we'll actually get:")
            print(output_fields)
            print("\n\n")
            raise(SystemExit(0))

        # Write new CSV file and call it originalname_slim.csv.
        filename2 = filename.replace('.csv', '_slim.csv')
        with open(filename2, 'w') as csvfile2:
            writer = csv.DictWriter(
                csvfile2, dialect=dialect, fieldnames=output_fields,
                escapechar='\\'
            )
            writer.writeheader()
            for row in sortedlist:
                writer.writerow({
                    col: row[col] for col in output_fields
                })

    print("File slimified: {}\n".format(filename2))

if __name__ == '__main__':
    csv_slimify()
