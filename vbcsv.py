#!/usr/bin/env python2
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
@click.option('--type', '-t', type=click.Choice(['vb', 'pp']), default="vb",
    help="which type of CSV modification?",)
@click.option('--dry-run', '-n', is_flag=True, default=False,
      help="don't write CSV file, just print data on console")
def csv_slimify(filename, verbose, type, dry_run):
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
    log.debug("### DEBUG: 1st 200 bytes... ###")
    log.debug(repr(open(filename, 'rb').read(200)))
    log.debug("\n")

    # cleanup csv file -> replace NUL characters
    fi = open(filename, 'rb')
    data = fi.read()
    fi.close()
    fo = open(filename, 'wb')
    #fo.write(data.replace('\x00', ''))
    fo.write(data.replace(b'\x00', ''))
    fo.close()

    # guess csv files dialect?
    with open(filename, 'rb') as csvfile:
      dialect = csv.Sniffer().sniff(csvfile.read(1024))
      log.info('Detected the following details about the "CSV dialect":')
      log.info('quotechar: {}'.format(dialect.quotechar))
      log.info('delimiter: {}'.format(dialect.delimiter))
      log.info('doublequote: {}'.format(dialect.doublequote))
      log.info("\n")
      # what's this?? why needed? -> Sets back file handle to beginning of file
      csvfile.seek(0)

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

      # this is is what we finally want in the output
      output_fields = ['Umsatzzeit', 'Buchungsdatum', 'Valutadatum', 'Betrag', 'Buchungstext', 'Umsatztext']

      # format Umsatzzeit so we can use it for sorting
      # and strip useless spaces in Buchungstext
      csv_dict_uz_replaced = []
      for idx,row in enumerate(csv_dict):
        #log.info('this is csv_dict idx, row: {}, {}'.format(idx, row))
        csv_dict_uz_replaced.append(row)
        for item in row.items():
          if item[0] == 'Umsatzzeit':
            uz_date_o = datetime.strptime(item[1], '%Y-%m-%d-%H.%M.%S.%f')
            uz_str = '{} {}'.format(uz_date_o.date(), uz_date_o.time().strftime('%H:%M:%S'))
            csv_dict_uz_replaced[idx]['Umsatzzeit'] = uz_str
          if item[0] == 'Umsatztext':
            #print(item[1])
            csv_dict_uz_replaced[idx]['Umsatztext'] = re.sub('\s+', ' ', item[1])

      # -> using lambda for sorting the list
      sortedlist = sorted(csv_dict_uz_replaced, key=lambda foo: (foo['Valutadatum'].lower()), reverse=False)
      log.info("sortedlist type is {}".format(sortedlist.__repr__))

      # on dry-runs we only output what would be written to csv and exit
      if dry_run:
        print(output_fields)
        for row in sortedlist:
          row_str = ''
          for item in row.items():
            row_str+= '| {} '.format(item[1])
          print('{}\n'.format(row_str))
        print('FIXME: Above fields are in the wrong order, this is what we finally want:')
        print(output_fields)
        print('\n\n')
        raise(SystemExit(0))

      # write new csv file
      filename2 = string.replace(filename, '.csv', '_slim.csv')
      with open(filename2, 'wb') as csvfile2:
        writer = csv.DictWriter(csvfile2, dialect=dialect, fieldnames=output_fields)
        writer.writeheader()
        for row in sortedlist:
          writer.writerow({'Umsatzzeit': row['Umsatzzeit'], 'Buchungsdatum': row['Buchungsdatum'], 'Valutadatum': row['Valutadatum'], 'Betrag': row['Betrag'].replace(".", ""), 'Buchungstext': row['Buchungstext'], 'Umsatztext': row['Umsatztext']})

    print("File slimified: {}\n".format(filename2))

if __name__ == '__main__':
    csv_slimify()