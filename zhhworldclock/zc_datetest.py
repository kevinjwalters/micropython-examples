
from datecalc import DateCalc


epoch = (1970, 1, 1,  0, 0, 0,  3,  1)

time = list(epoch)
print(time)
for count in range(400):
    DateCalc.add(time, 86400)
    print(time)

print()

DateCalc.add(time, 400 * -86400)
print(time)

print()

for count in range(400):
    DateCalc.add(time, -86400)
    print(time)
