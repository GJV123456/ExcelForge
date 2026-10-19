import { classificationProfile as T19 } from './T19/classification.js'

export const classificationProfiles = { T19 }
export const getClassificationProfile = (code = 'T19') => classificationProfiles[String(code || 'T19').toUpperCase()] || T19
