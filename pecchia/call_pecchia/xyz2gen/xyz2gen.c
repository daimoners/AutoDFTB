#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>

#define SQRT3 1.732050808
#define SQRT6 2.449489743

int main(int argc,char *argv[]){

FILE *FPin;
char **atm,*filein, *tmpstr;
int i,j,nsp,natm,*isp,cnt,nchar;
double *x,*y,*z;
double aa, bb, cc;
int supercell;

if (argc<2)
{ 
  printf("Usage: xyz2gen filein [-s] [a b c]\n");
  printf("filein - structure.xyz input file\n");
  printf(" -s :    set supercell\n");
  printf("a b c:   orthorombic supercell lengths\n");
  return 1;
}

supercell=0;
filein=malloc(60*sizeof(char));
tmpstr=malloc(90*sizeof(char));
strcpy(filein,argv[1]);  

if (argc>=3)
{
   if (strcmp(argv[2],"-s")==0)
   {
     supercell=1;
   }
}

if (supercell && argc==6){
  aa = atof(argv[3]);  
  bb = atof(argv[4]);  
  cc = atof(argv[5]);  
}


FPin=fopen(filein,"r");
if (!FPin)
  { 
    printf("File error or doesn't exist\n");
    free(filein);
    return 2;
  }

fgets(tmpstr,90,FPin);
sscanf(tmpstr," %d",&natm);
fgets(tmpstr,90,FPin);

atm=malloc(natm*sizeof(char *));
for (i=0;i<natm;i++)
  {
    atm[i]=malloc(2*sizeof(char));
  }

isp=malloc(natm*sizeof(int));
x=malloc(natm*sizeof(double));
y=malloc(natm*sizeof(double));
z=malloc(natm*sizeof(double));
 
for(i=0;i<natm;i++)
 {
   fgets(tmpstr,90,FPin);
   sscanf(tmpstr," %s %lf %lf %lf",atm[i],x+i,y+i,z+i);
 }

fclose(FPin);

nsp=0;
isp[0]=1;

for(i=1;i<natm;i++)
  {
   cnt=1;
   for(j=0;j<=nsp;j++)
     {
       if(strcmp(atm[j],atm[i])==0){cnt=0; isp[i]=j+1;}
     }

   if(cnt>0){ nsp++; strcpy(atm[nsp],atm[i]); isp[i]=nsp+1; }

  }


if (supercell)
{
  printf(" %d %c\n",natm,'S');
}
else
{
  printf(" %d %c\n",natm,'C');
}

for(i=0;i<=nsp;i++)
  {
   printf(" %s",atm[i]);
  }

printf("\n");


for(i=0;i<natm;i++)
  { 
    printf("%d ", i+1);
    nchar = floor( log10(1.0*natm)-log10(1.0*(i+1)) );
    for (j=0;j<nchar;j++){printf(" ");}
    printf("%d %18.12f %18.12f %18.12f\n",isp[i],x[i],y[i],z[i]);
  }

if (supercell)
{
    printf("0.000000000000 0.0000000000000 0.0000000000000\n");
    printf("%18.12f 0.000000000000 0.0000000000000 \n",aa);
    printf("0.000000000000 %18.12f 0.0000000000000 \n",bb);
    printf("0.000000000000 0.0000000000000 %18.12f \n",cc);
}

free(filein);
free(tmpstr);
for(i=0;i<natm;i++){ free(atm[i]); }
free(atm);
free(x); free(y); free(z); free(isp);

}
	 	
    /* printf("HETATM%5d%3s%12d     %6.3f  %6.3f  %6.3f\n",i,atm[ind],i,x,y,z);*/	 	
