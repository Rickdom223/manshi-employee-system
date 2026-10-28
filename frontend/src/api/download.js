import {http} from './http'
export async function download(url,params,name){try{const response=await http.get(url,{params,responseType:'blob'});const link=document.createElement('a');link.href=URL.createObjectURL(response);link.download=name+'.xlsx';link.click();setTimeout(()=>URL.revokeObjectURL(link.href),1000)}catch{}}
