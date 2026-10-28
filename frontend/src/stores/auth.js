import { reactive } from 'vue'
import {useTabsStore} from './tabs'
import {pinia} from './pinia'
export const auth = reactive({ user: null, csrf: '', ready:false })
export function clearAuth() { auth.user=null;auth.csrf='';useTabsStore(pinia).resetTabs() }
