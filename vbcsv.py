#!/usr/bin/python

import sys
import csv
import string
import zipfile
import pprint
from subprocess import call

# puts field data to lower case
def lower_getter(field):
  def _getter(obj):
      return obj[field].lower()
  return _getter

# used like this
#list_of_dicts.sort(key=lower_getter(key_field)) 

if len(sys.argv) > 1:
  filename = sys.argv[1]
  if "/" in filename:
    filenamepath=filename.rsplit('/',1)[0]
    filenamefile=filename.rsplit('/',1)[1]
    filename=filenamepath+"/"+filenamefile
  print ("file used: " + str(filename))
  #if ".zip" in filename:
  #  print ("filename contains .zip, extracting "+str(filenamefile)+" to path "+str(filenamepath)+" ...\n")
  #  with zipfile.ZipFile(filename, "r") as z:
  #    z.extractall(filenamepath)
  #    #filename = string.replace(filename, '.zip', '.csv')
  #    filenamefile = string.replace(filenamefile, '.zip', '.csv')
  #    filenamefile = "subscribed_"+filenamefile
  #    filename=filenamepath+"/"+filenamefile
else:
  print "please provide csv file!"
  raise sys.exit()

# DEBUG dump 1st 200 bytes
#print "### DEBUG: 1st 200 bytes... ###"
#print repr(open('members_export_f664863d54.csv', 'rb').read(200))
#print ""

# cleanup csv file -> replace NUL characters 
fi = open(filename, 'rb')
data = fi.read()
fi.close()
fo = open(filename, 'wb')
fo.write(data.replace('\x00', ''))
fo.close()

# guess csv files dialect?
with open(filename, 'rb') as csvfile:
  dialect = csv.Sniffer().sniff(csvfile.read(1024))
  #print dialect.quotechar
  #print dialect.delimiter
  #print dialect.doublequote
  # what's this?? why needed?
  csvfile.seek(0)

  reader = csv.DictReader(csvfile, dialect=dialect)
  #print reader.fieldnames 

  # how does data actually look like?
  #for row in reader:
  #  pp = pprint.PrettyPrinter(indent=4, depth=1)
  #  pp.pprint(row)
  

  # -> using lambda, why te hell was itemgetter necessary??
  sortedlist = sorted(reader, key=lambda foo: (foo['Umsatzzeit'].lower()), reverse=False)
  # debug output sortedlist
  #for row in sortedlist:
    #print row['Valutadatum'], row['Betrag'], row['Buchungstext'], row['Umsatztext']

  # write new csv file 
  filename2 = string.replace(filename, '.csv', '_slim.csv')
  with open(filename2, 'wb') as csvfile2:
    writer = csv.DictWriter(csvfile2, dialect=dialect, fieldnames=['Valutadatum', 'Umsatzzeit', 'Betrag', 'Buchungstext', 'Umsatztext']) 
    writer.writeheader()
    for row in sortedlist:
      #print row['E-Mail Adresse'], row['First Name'], row['Last Name']
      writer.writerow({'Valutadatum': row['Valutadatum'], 'Umsatzzeit': row['Umsatzzeit'], 'Betrag': row['Betrag'], 'Buchungstext': row['Buchungstext'], 'Umsatztext': row['Umsatztext']})

print "file written: " + str(filename2)

