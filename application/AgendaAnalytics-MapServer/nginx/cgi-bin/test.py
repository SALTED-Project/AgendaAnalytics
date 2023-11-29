#!/usr/local/bin/python3
import art
Art=art.text2art("TEST",font='block',chr_ignore=True)

print('Content-Type: text/plain')
print('')
print('This "is" my test!')
print(Art)
