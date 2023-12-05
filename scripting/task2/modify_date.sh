#!/usr/bin/env bash

fname="AlphaTechConsultigEmployees_cleaned.csv"
bname=$(echo "$fname" | awk 'BEGIN{FS="."}; {print $1}')

# keep all columns except for the "DateofBirth" column
awk 'BEGIN{FS=",";ORS=","}; {for(ii=1;ii<12;ii++) {print $ii}}; {print "\n"}' "$fname" > file1.txt
awk 'BEGIN{FS=",";ORS=","}; {for(ii=13;ii<=NF;ii++) {print $ii}}; {print "\n"}' "$fname" > file2.txt
sed -i 's#,$##g' file2.txt

# modify DateofBirth
cdate=$(date | awk '{print $7}')
awk 'BEGIN{FS=","}; {if (NR>1) {print $12}}' "$fname" | 
awk -v cdate=$cdate 'BEGIN{print("DateofBirth,");FS="/";OFS="/"}; {if (2000+$3>cdate) {print $1,$2,"19"$3} 
                                             else {print $1,$2,"20"$3}}' > modified_date.txt

# assemble data
paste -d "" file1.txt modified_date.txt file2.txt > "$bname"_datefix.csv

# clean up
rm file1.txt
rm file2.txt
rm modified_date.txt
