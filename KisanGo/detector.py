import io
import json
import logging
import os
from typing import Optional, List
from PIL import Image

from models import CropDiagnosis, TreatmentPlan
from services.disease_model import diagnose_image
from services.treatment import get_guidance
from services.scheme_engine import find_potentially_relevant_schemes

logger = logging.getLogger("agridoc.detector")

# Localized disease names and terms for Hindi and Marathi
TRANSLATIONS = {
    "Tomato___healthy": {
        "hi": {
            "disease": "स्वस्थ पौधा (Healthy)",
            "symptoms": "पत्ती पर कोई बीमारी के लक्षण नहीं हैं। पत्तियां हरी और स्वस्थ हैं।",
            "actions": ["किसी उपचार की आवश्यकता नहीं है।", "सप्ताह में दो बार नियमित निगरानी जारी रखें।"],
            "prevention": ["पौधों के बीच पर्याप्त हवा का संचार रखें।", "जड़ों में पानी दें, पत्तियों को गीला न करें।", "हर मौसम में फसल चक्र अपनाएं।"],
            "warning": "यदि बाद में पत्तों पर कोई धब्बे या पीलापन दिखे तो पुनः फोटो भेजें।"
        },
        "mr": {
            "disease": "निरोगी पीक (Healthy)",
            "symptoms": "पानांवर कोणत्याही रोगाची लक्षणे नाहीत. पाने पूर्णपणे हिरवी आणि निरोगी आहेत.",
            "actions": ["कोणत्याही उपचाराची गरज नाही.", "आठवड्यातून दोनदा नियमित पाहणी सुरू ठेवावी."],
            "prevention": ["झाडांमध्ये योग्य अंतर ठेवा जेणेकरून हवा खेळती राहील.", "मुळांशी पाणी द्या, पानांवर पाणी उडवणे टाळा.", "पिकांची फेरपालट करा."],
            "warning": "पानांवर डाग किंवा पिवळेपणा आढळल्यास लगेच पुन्हा फोटो पाठवा."
        },
        "ta": {   'actions': ['எந்த சிகிச்சையும் தேவையில்லை.', 'வாரம் இருமுறை தொடர்ந்து கண்காணிக்கவும்.'],
            'disease': 'ஆரோக்கியமான பயிர் (Healthy)',
            'prevention': [   'காற்றோட்டத்திற்காக சரியான இடைவெளியை பராமரிக்கவும்.',
                              'அடிமரத்தில் தண்ணீர் ஊற்றவும், இலைகளை நனைக்க வேண்டாம்.',
                              'பயிர் சுழற்சியை பின்பற்றவும்.'],
            'symptoms': 'நோய்க்கான அறிகுறிகள் எதுவும் இல்லை. இலைகள் பச்சையாகவும் ஆரோக்கியமாகவும் உள்ளன.',
            'warning': 'பின்னராவது புள்ளிகள் அல்லது மஞ்சள் நிறம் தோன்றினால் மீண்டும் புகைப்படம் அனுப்பவும்.'}
    },
    "Tomato___Early_blight": {
        "hi": {
            "disease": "अगेती झुलसा (Early Blight - Alternaria solani)",
            "symptoms": "निचली और पुरानी पत्तियों पर गहरे भूरे गोल छल्ले (Target spots) जैसे धब्बे, धब्बों के चारों ओर पीलापन।",
            "actions": [
                "संक्रमित निचली पत्तियों को तुरंत तोड़कर खेत से दूर नष्ट करें।",
                "पौधों के बीच हवा का प्रवाह बढ़ाएं और ऊपर से पानी का छिड़काव बंद करें।",
                "रोग फैलने पर स्थानीय कृषि विभाग / KVK या लाइसेंस प्राप्त डीलर से अनुमोदित कवकनाशी (Fungicide) की सही मात्रा की सलाह लें।"
            ],
            "prevention": [
                "प्रमाणित और रोगमुक्त बीजों/पौधों का प्रयोग करें।",
                "टमाटर और आलू की लगातार उसी खेत में 2-3 मौसम तक बुवाई न करें (फसल चक्र अपनाएं)।",
                "फसल कटाई के बाद पुराने अवशेषों को खेत से नष्ट कर दें।"
            ],
            "warning": "अगेती झुलसे से उपज में भारी नुकसान हो सकता है। कीटनाशक खरीदने से पहले कृषि अधिकारी से पुष्टि करें।"
        },
        "mr": {
            "disease": "लवकर येणारा करपा (Early Blight - Alternaria solani)",
            "symptoms": "खालच्या जुन्या पानांवर काळे-तपकिरी गोलाकार चक्रासारखे (Target) डाग आणि डागांच्या भोवती पिवळेपणा.",
            "actions": [
                "बाधित झालेली खालची पाने काढून शेतातून दूर नष्ट करा.",
                "झाडांमध्ये हवा खेळती ठेवा आणि पानांवर पाणी उडवणे थांबवा.",
                "रोग वाढल्यास स्थानिक कृषी विभाग / KVK किंवा परवानाधारक कृषी केंद्राकडून योग्य बुरशीनाशकाचा सल्ला घ्या."
            ],
            "prevention": [
                "प्रमाणित रोगमुक्त बियाणे किंवा रोपे वापरा.",
                "टोमॅटो/बटाट्यांची सलग त्याच जमिनीत लागवड टाळा (पिकांची फेरपालट करा).",
                "कापणीनंतर पिकांचे जुने अवशेष जाळून किंवा गाडून नष्ट करा."
            ],
            "warning": "नियंत्रण न केल्यास उत्पादनात मोठी घट होऊ शकते. उपचारापूर्वी कृषी अधिकाऱ्यांचा सल्ला घ्या."
        },
        "ta": {   'actions': [   'பாதிக்கப்பட்ட இலைகளை உடனடியாக அகற்றி அழிக்கவும்.',
                           'காற்றோட்டத்தை அதிகரிக்கவும், மேலே இருந்து தண்ணீர் ஊற்றுவதை நிறுத்தவும்.',
                           'பரிந்துரைக்கப்பட்ட பூஞ்சைக் கொல்லியை (Fungicide) பயன்படுத்தவும்.'],
            'disease': 'முன் இலைக்கருகல் (Early Blight)',
            'prevention': [   'சான்றளிக்கப்பட்ட நோய் இல்லாத விதைகளை பயன்படுத்தவும்.',
                              'பயிர் சுழற்சியை பின்பற்றவும்.',
                              'அறுவடைக்கு பின் எச்சங்களை அழிக்கவும்.'],
            'symptoms': 'பழைய இலைகளில் பழுப்பு நிற வட்டமான புள்ளிகள் (Target spots) மற்றும் அவற்றை சுற்றி மஞ்சள் நிறம்.',
            'warning': 'கடும் பாதிப்பு ஏற்பட்டால் மகசூல் குறையும். மருந்து வாங்கும் முன் விவசாய அதிகாரியை அணுகவும்.'}
    },
    "Tomato___Late_blight": {
        "hi": {
            "disease": "पछेती झुलसा (Late Blight - Phytophthora infestans)",
            "symptoms": "पत्तियों और तनों पर पानी से भीगे हुए काले-भूरे धब्बे जो तेजी से फैलते हैं; नम मौसम में पत्तियों के नीचे सफेद फफूंद।",
            "actions": [
                "यह रोग ठंडे और नम मौसम में बहुत तेजी से फैलता है — तुरंत कार्रवाई करें।",
                "गंभीर रूप से प्रभावित पौधों और पत्तियों को उखाड़कर नष्ट करें (खाद न बनाएं)।",
                "ऊपर से सिंचाई तुरंत रोकें; पत्तों को सूखा रखें।",
                "तुरंत अपने स्थानीय कृषि विभाग / KVK से संपर्क करें।"
            ],
            "prevention": [
                "प्रमाणित रोगमुक्त पौधे लगाएं।",
                "स्प्रिंकलर से पानी देने से बचें, ड्रिप सिंचाई अपनाएं।",
                "आसपास के जंगली सोलानेसी खरपतवार नष्ट करें।"
            ],
            "warning": "पछेती झुलसा अत्यंत विनाशकारी रोग है जो 1-2 हफ्तों में पूरी फसल नष्ट कर सकता है। इसे कतई नजरअंदाज न करें।"
        },
        "mr": {
            "disease": "उशिरा येणारा करपा (Late Blight - Phytophthora infestans)",
            "symptoms": "पाने व खोडावर पाण्यासारखे ओले काळपट डाग जे वेगाने वाढतात; दमट हवेत पानाच्या मागे पांढरी बुरशी दिसते.",
            "actions": [
                "थंड आणि दमट हवामानात हा रोग अत्यंत वेगाने पसरतो — तातडीने उपाययोजना करा.",
                "बाधित पाने आणि रोपे उपटून नष्ट करा (खत खड्ड्यात टाकू नका).",
                "तुषार सिंचन लगेच बंद करा, पाने कोरडी ठेवा.",
                "तातडीने जवळच्या कृषी विज्ञान केंद्राशी (KVK) संपर्क साधा."
            ],
            "prevention": [
                "प्रमाणित रोगमुक्त रोपे लावा.",
                "ठिबक सिंचनाचा वापर करा जेणेकरून पाने भिजणार नाहीत.",
                "शेताभोवतालचे तण काढून टाका."
            ],
            "warning": "हा अत्यंत घातक रोग असून काही दिवसांत संपूर्ण पीक नष्ट करू शकतो. त्वरित पावले उचला."
        },
        "ta": {   'actions': [   'இது மிக வேகமாக பரவக்கூடியது — உடனடியாக செயல்படவும்.',
                           'பாதிக்கப்பட்ட செடிகளை பிடுங்கி அழிக்கவும்.',
                           'மேலே இருந்து தண்ணீர் ஊற்றுவதை உடனடியாக நிறுத்தவும்.',
                           'விவசாய அதிகாரியை உடனடியாக தொடர்பு கொள்ளவும்.'],
            'disease': 'பின் இலைக்கருகல் (Late Blight)',
            'prevention': [   'நோய் இல்லாத செடிகளை நடவும்.',
                              'சொட்டு நீர் பாசனத்தை பயன்படுத்தவும்.',
                              'சுற்றியுள்ள களைகளை அழிக்கவும்.'],
            'symptoms': 'இலைகள் மற்றும் தண்டுகளில் வேகமாக பரவும் கருப்பு/பழுப்பு நிற புள்ளிகள்; இலைகளின் அடியில் வெள்ளை '
                        'பூஞ்சை.',
            'warning': 'இது முழு பயிரையும் 1-2 வாரங்களில் அழித்துவிடும். உடனடியாக நடவடிக்கை எடுக்கவும்.'}
    },
    "Tomato___Leaf_Mold": {
        "hi": {
            "disease": "पत्ती का फफूंद (Leaf Mold - Passalora fulva)",
            "symptoms": "पत्ती की ऊपरी सतह पर हल्के हरे/पीले धब्बे और निचली सतह पर जैतून-हरे से बैंगनी रंग की मखमली फफूंद।",
            "actions": [
                "पौधों के आसपास हवा का प्रवाह बढ़ाएं और नमी कम करें।",
                "सबसे अधिक प्रभावित पत्तियों को तोड़कर नष्ट करें।",
                "जड़ों में पानी दें, पत्तियों को सूखा रखें।"
            ],
            "prevention": [
                "प्रतिरोधी किस्में लगाएं।",
                "पॉलीहाउस या खेत में पौधों के बीच उचित दूरी रखें।",
                "फसल अवशेषों को नष्ट करें।"
            ],
            "warning": "यह रोग अधिक आर्द्रता (85% से ऊपर) में पनपता है। हवा का संचार सुधारें।"
        },
        "mr": {
            "disease": "पानावरील बुरशी (Leaf Mold - Passalora fulva)",
            "symptoms": "पानाच्या वरच्या भागावर पिवळसर डाग आणि खालच्या बाजूला ऑलिव्ह-हिरवी किंवा जांभळट मऊ बुरशी.",
            "actions": [
                "हवा खेळती ठेवा आणि झाडांमधील आर्द्रता कमी करा.",
                "जास्त बाधित पाने तोडून नष्ट करा.",
                "मुळांशी पाणी द्या, पानांवर पाणी शिंपडू नका."
            ],
            "prevention": [
                "रोगप्रतिकारक वाण वापरा.",
                "पॉलीहाऊस किंवा शेतात रोपांमध्ये योग्य अंतर ठेवा.",
                "हवेतील दमटपणा कमी ठेवण्याचा प्रयत्न करा."
            ],
            "warning": "दमट हवामानात हा रोग वाढतो. स्थानिक कृषी सहाय्यकांचा सल्ला घ्या."
        },
        "ta": {   'actions': [   'காற்றோட்டத்தை மேம்படுத்தி ஈரப்பதத்தை குறைக்கவும்.',
                           'மிகவும் பாதிக்கப்பட்ட இலைகளை அகற்றி அழிக்கவும்.',
                           'அடிமரத்தில் மட்டும் தண்ணீர் ஊற்றவும்.'],
            'disease': 'இலை பூஞ்சை (Leaf Mold)',
            'prevention': [   'நோய் எதிர்ப்பு ரகங்களை பயன்படுத்தவும்.',
                              'செடிகளுக்கு இடையே சரியான இடைவெளி விடவும்.',
                              'பயிர் எச்சங்களை அழிக்கவும்.'],
            'symptoms': 'இலைகளின் மேல் வெளிர் மஞ்சள் புள்ளிகள் மற்றும் அடியில் பச்சை-ஊதா நிற பூஞ்சை.',
            'warning': 'அதிக ஈரப்பதத்தில் (85%+) இது வேகமாக வளரும்.'}
    },
    "Tomato___Septoria_leaf_spot": {
        "hi": {
            "disease": "सेप्टोरिया लीफ स्पॉट (Septoria Leaf Spot)",
            "symptoms": "काले किनारों और हल्के भूरे/धूसर केंद्र वाले छोटे गोल धब्बे, केंद्र में काले बिंदु दिखते हैं।",
            "actions": [
                "प्रभावित निचली पत्तियों को तुरंत तोड़कर नष्ट करें।",
                "गीली पत्तियों में काम करने से बचें ताकि रोग न फैले।",
                "पौधों के बीच हवा का प्रवाह बेहतर करें।"
            ],
            "prevention": [
                "कम से कम 2 वर्षों तक टमाटर/आलू के साथ फसल चक्र अपनाएं।",
                "जमीन से पत्तियों पर मिट्टी के छींटे रोकने के लिए मल्चिंग करें।",
                "जड़ों में सिंचाई करें।"
            ],
            "warning": "इसे अगेती झुलसा न समझें — सेप्टोरिया के धब्बे छोटे होते हैं। सही पुष्टि के लिए KVK से संपर्क करें।"
        },
        "mr": {
            "disease": "सेप्टोरिया पानावरील ठिपके (Septoria Leaf Spot)",
            "symptoms": "गडद कडा आणि मध्यभागी करड्या रंगाचे लहान गोलाकार ठिपके; मध्यभागी बारीक काळे ठिपके दिसतात.",
            "actions": [
                "खालची बाधित पाने तोडून त्वरित नष्ट करा.",
                "पाने ओली असताना शेतात काम करू नका, जेणेकरून रोग इतरत्र पसरणार नाही.",
                "झाडांमध्ये हवा खेळती राहील अशी व्यवस्था करा."
            ],
            "prevention": [
                "किमान २ वर्षे टोमॅटो/बटाट्यांची फेरपालट करा.",
                "मातीचे थेंब पानांवर उडू नयेत म्हणून आच्छादन (Mulching) करा.",
                "तुषार सिंचन टाळा."
            ],
            "warning": "उपचाराने फरक न पडल्यास कृषी अधिकाऱ्यांकडून खात्री करून घ्या."
        },
        "ta": {   'actions': [   'பாதிக்கப்பட்ட கீழ் இலைகளை அகற்றி அழிக்கவும்.',
                           'இலைகள் ஈரமாக இருக்கும்போது செடிகளில் வேலை செய்வதை தவிர்க்கவும்.',
                           'காற்றோட்டத்தை அதிகரிக்கவும்.'],
            'disease': 'செப்டோரியா இலைப்புள்ளி (Septoria Leaf Spot)',
            'prevention': [   '2 ஆண்டுகள் பயிர் சுழற்சியை பின்பற்றவும்.',
                              'மண்ணிலிருந்து தண்ணீர் இலைகளில் படுவதை தடுக்க மூடாக்கு (Mulching) பயன்படுத்தவும்.',
                              'சொட்டு நீர் பாசனத்தை பயன்படுத்தவும்.'],
            'symptoms': 'சிறிய வட்ட புள்ளிகள், கருப்பு விளிம்புகள் மற்றும் சாம்பல் நிற மையத்துடன் காணப்படும்.',
            'warning': 'இதை முன் இலைக்கருகல் என தவறாக நினைக்க வேண்டாம். சரியான மருந்துக்கு அதிகாரியை அணுகவும்.'}
    },
    "Tomato___Spider_mites_Two_spotted_spider_mite": {
        "hi": {
            "disease": "लाल मकड़ी कीट प्रकोप (Two-Spotted Spider Mite - Pest)",
            "symptoms": "पत्तियों पर बारीक पीले/सफेद बिंदु, पत्तियां कांस्य या पीली होकर सूखती हैं; पत्तियों के नीचे बारीक जाला दिखता है।",
            "actions": [
                "हल्के प्रकोप में पत्तियों के नीचे तेज पानी की धार से स्प्रे करें ताकि मकड़ियां बह जाएं।",
                "अत्यधिक नाइट्रोजन खाद देने से बचें, जिससे इनकी संख्या बढ़ती है।",
                "गंभीर प्रकोप होने पर कृषि विभाग द्वारा अनुमोदित कीटनाशक (Miticide) का प्रयोग करें।"
            ],
            "prevention": [
                "पौधों में पर्याप्त नमी बनाए रखें — सूखे पौधों पर मकड़ी तेजी से हमला करती है।",
                "मित्र कीटों (लेडीबर्ड बीटल आदि) का संरक्षण करें।",
                "गर्म और शुष्क मौसम में नियमित निरीक्षण करें।"
            ],
            "warning": "यह फफूंद या जीवाणु रोग नहीं है, बल्कि एक कीट है — इसका उपचार फफूंदनाशक से नहीं होता।"
        },
        "mr": {
            "disease": "लाल कोळी कीड प्रादुर्भाव (Two-Spotted Spider Mite - Pest)",
            "symptoms": "पानांवर बारीक पिवळे-पांढरे ठिपके, पाने सुकणे आणि पानाच्या मागच्या बाजूला बारीक जाळे दिसणे.",
            "actions": [
                "कमी प्रादुर्भाव असल्यास पानाच्या खालच्या भागावर पाण्याचा जोरदार फवारा मारा.",
                "जास्त नत्र (युरिया) खत देणे टाळा, ज्यामुळे कोळींची संख्या वाढते.",
                "जास्त प्रादुर्भाव असल्यास कृषी केंद्राच्या सल्ल्याने योग्य कोळीनाशकाची फवारणी करा."
            ],
            "prevention": [
                "झाडांना पाण्याचा ताण पडू देऊ नका.",
                "मित्र कीटकांचे संरक्षण करा.",
                "उष्ण आणि कोरड्या हवामानात सातत्याने पाहणी करा."
            ],
            "warning": "हा बुरशीजन्य रोग नसून कीड आहे — यासाठी बुरशीनाशक काम करत नाही."
        },
        "ta": {   'actions': [   'சிலந்திப் பேன் கொல்லியை (Miticide/Acaricide) பயன்படுத்தவும்.',
                           'பாதிக்கப்பட்ட பகுதிகளை அகற்றி அழிக்கவும்.',
                           'இலைகளின் அடியில் தண்ணீரை பீய்ச்சி அடிக்கவும்.'],
            'disease': 'சிலந்திப் பேன் (Spider Mites)',
            'prevention': ['வயலை சுற்றியுள்ள களைகளை கட்டுப்படுத்தவும்.', 'வறண்ட வெப்பமான வானிலையில் தொடர்ந்து கண்காணிக்கவும்.'],
            'symptoms': 'இலைகளில் சிறிய மஞ்சள் புள்ளிகள், செடியின் மீது மெல்லிய வலைகள் காணப்படும்.',
            'warning': 'இது பூஞ்சை அல்ல, பூச்சி. பூஞ்சைக் கொல்லிகள் வேலை செய்யாது.'}
    },
    "Tomato___Tomato_mosaic_virus": {
        "hi": {
            "disease": "टमाटर मोज़ेक वायरस (Tomato Mosaic Virus - ToMV)",
            "symptoms": "पत्तियों पर हल्के और गहरे हरे रंग का चितकबरा (Mosaic) पैटर्न, पत्तियां मुड़ना और पौधों का बौना होना।",
            "actions": [
                "वायरस जनित रोगों की कोई रासायनिक दवा नहीं होती — मुख्य ध्यान फैलाव रोकने पर होता है।",
                "संक्रमित पौधों को तुरंत उखाड़कर नष्ट करें ताकि स्वस्थ पौधों में न फैले।",
                "रोगग्रस्त पौधों को छूने के बाद साबुन से हाथ और औजार साफ करें।",
                "तंबाकू उत्पादों का उपयोग करने के बाद पौधों को न छुएं।"
            ],
            "prevention": [
                "प्रमाणित वायरस-मुक्त बीज और प्रतिरोधी किस्मों का उपयोग करें।",
                "कटाई-छंटाई करते समय औजारों को रोगाणुरहित करें।",
                "आसपास के खरपतवार नष्ट करें जो वायरस के वाहक हो सकते हैं।"
            ],
            "warning": "संक्रमित पौधा ठीक नहीं हो सकता — पूरे खेत को बचाने के लिए प्रभावित पौधे को नष्ट करना ही एकमात्र उपाय है।"
        },
        "mr": {
            "disease": "टोमॅटो मोझॅक व्हायरस (Tomato Mosaic Virus - ToMV)",
            "symptoms": "पानांवर फिकट व गडद हिरव्या रंगाचे मोझॅक डाग, पाने चुरमुरणे आणि झाडाची वाढ खुंटणे.",
            "actions": [
                "विषाणूजन्य रोगांवर कोणतेही रासायनिक औषध नाही — रोग इतर झाडांवर पसरण्यापासून रोखणे हाच उपाय आहे.",
                "बाधित झाडे मुळासकट उपटून नष्ट करा.",
                "झाडांना स्पर्श केल्यानंतर हात आणि अवजारे साबणाच्या पाण्याने धुवा.",
                "तंबाखू उत्पादने वापरल्यानंतर रोपांना हात लावू नका."
            ],
            "prevention": [
                "प्रमाणित विषाणूमुक्त बियाणे आणि प्रतिकारक्षम वाण वापरा.",
                "छाटणी करताना अवजारे निर्जंतुक करा.",
                "शेतातील तण नष्ट करा."
            ],
            "warning": "विषाणूबाधित झाड बरे होऊ शकत नाही — उर्वरित पीक वाचवण्यासाठी बाधित झाड नष्ट करा."
        },
        "ta": {   'actions': [   'வைரஸ் நோய்களுக்கு ரசாயன மருந்து இல்லை — பரவாமல் தடுப்பதே முக்கியம்.',
                           'பாதிக்கப்பட்ட செடிகளை உடனடியாக பிடுங்கி அழிக்கவும்.',
                           'செடிகளை தொட்ட பின் கைகளையும் கருவிகளையும் சோப்பால் கழுவவும்.'],
            'disease': 'தக்காளி மொசைக் வைரஸ் (Tomato Mosaic Virus)',
            'prevention': [   'வைரஸ் இல்லாத விதைகளை பயன்படுத்தவும்.',
                              'கத்தரிக்கும் கருவிகளை கிருமி நீக்கம் செய்யவும்.',
                              'களைகளை அழிக்கவும்.'],
            'symptoms': 'இலைகளில் வெளிர் மற்றும் அடர் பச்சை நிற புள்ளிகள், இலை சுருக்கம் மற்றும் வளர்ச்சி குன்றுதல்.',
            'warning': 'பாதிக்கப்பட்ட செடியை குணப்படுத்த முடியாது. மற்ற செடிகளை காக்க அதை அழிப்பதே ஒரே வழி.'}
    }
}


def build_whatsapp_summary(
    crop: str,
    disease_name: str,
    confidence: float,
    symptoms: str,
    actions: List[str],
    prevention: List[str],
    warning: str,
    source: Optional[str],
    schemes: List[dict],
    language: str = "en"
) -> str:
    """Formats an attractive, clear WhatsApp message matching the agricultural database."""
    lang = language.lower()

    if "mr" in lang or "marathi" in lang:
        msg = [
            f"🌿 *पीक:* {crop}",
            f"🦠 *रोग:* {disease_name}",
            f"📊 *अचूकता:* {confidence*100:.1f}%",
            f"⚠️ *लक्षणे:* {symptoms}",
            f"💊 *उपचार:* {actions[0] if actions else '-'}"
        ]
        return "\n".join(msg)

    elif "hi" in lang or "hindi" in lang:
        msg = [
            f"🌿 *फसल:* {crop}",
            f"🦠 *रोग:* {disease_name}",
            f"📊 *सटीकता:* {confidence*100:.1f}%",
            f"⚠️ *लक्षण:* {symptoms}",
            f"💊 *उपचार:* {actions[0] if actions else '-'}"
        ]
        return "\n".join(msg)

    elif "ta" in lang or "tamil" in lang:
        msg = [
            f"🌿 *பயிர்:* {crop}",
            f"🦠 *நோய்:* {disease_name}",
            f"📊 *நம்பகத்தன்மை:* {confidence*100:.1f}%",
            f"⚠️ *அறிகுறிகள்:* {symptoms}",
            f"💊 *சிகிச்சை:* {actions[0] if actions else '-'}"
        ]
        return "\n".join(msg)

    else:
        msg = [
            f"🌿 *Crop:* {crop}",
            f"🦠 *Disease:* {disease_name}",
            f"📊 *Confidence:* {confidence*100:.1f}%",
            f"⚠️ *Symptoms:* {symptoms}",
            f"💊 *Action:* {actions[0] if actions else '-'}"
        ]
        return "\n".join(msg)


def diagnose_crop_image(
    image_bytes: bytes,
    mime_type: str = "image/jpeg",
    user_caption: str = "",
    language: str = "en",
    model_name: Optional[str] = None,
    state: str = "All India"
) -> CropDiagnosis:
    """
    Analyzes crop image bytes using the PyTorch MobileNetV3-Small model
    and retrieves verified guidance from diseases.json and schemes.json.
    Zero LLM hallucination - 100% verified agricultural data.
    """
    try:
        image = Image.open(io.BytesIO(image_bytes))
    except Exception as exc:
        logger.error(f"Failed to read image bytes: {exc}")
        return CropDiagnosis(
            is_crop=False,
            crop_name="Unknown",
            is_healthy=False,
            condition_name="Unreadable Image",
            farmer_friendly_summary="⚠️ Could not process the uploaded photo. Please send a clear JPG or PNG image of the crop leaf! 📸"
        )

    # 1. Run local CV MobileNetV3 model
    diagnosis_raw = diagnose_image(image)
    raw_class = diagnosis_raw["raw_class"]
    crop = diagnosis_raw["crop"]
    confidence = diagnosis_raw["confidence"]
    is_low_conf = diagnosis_raw["low_confidence"]
    top_k = diagnosis_raw.get("top_k", [])

    lang_lower = language.lower()
    is_hi = "hi" in lang_lower or "hindi" in lang_lower
    is_mr = "mr" in lang_lower or "marathi" in lang_lower
    is_ta = "ta" in lang_lower or "tamil" in lang_lower

    # 2. Check low confidence
    if is_low_conf:
        if is_mr:
            low_conf_msg = (
                "⚠️ *अस्पष्ट फोटो किंवा कमी अचूकता*\n\n"
                f"सध्याच्या फोटोवरून पिकाचा रोग स्पष्टपणे ओळखता आला नाही (अचूकता: {confidence*100:.1f}%).\n\n"
                "📸 कृपया चांगल्या प्रकाशात बाधित पानाचा जवळून स्पष्ट फोटो पाठवा.\n"
                "तसेच आपल्या नजीकच्या कृषी विज्ञान केंद्राशी (KVK) किंवा कृषी सहाय्यकाशी संपर्क साधावा."
            )
        elif is_hi:
            low_conf_msg = (
                "⚠️ *अस्पष्ट फोटो या कम सटीकता*\n\n"
                f"इस फोटो से फसल के रोग की पुष्टि पर्याप्त सटीकता से नहीं हो पाई (सटीकता: {confidence*100:.1f}%).\n\n"
                "📸 कृपया अच्छी रोशनी में प्रभावित पत्ती का पास से साफ फोटो भेजें!\n"
                "यदि समस्या गंभीर है, तो कृपया अपने नजदीकी कृषि विज्ञान केंद्र (KVK) या कृषि अधिकारी से संपर्क करें।"
            )
        elif is_ta:
            low_conf_msg = (
                "⚠️ *குறைந்த துல்லியம்*\n\n"
                f"இந்த புகைப்படத்திலிருந்து நோயை துல்லியமாக கண்டறிய முடியவில்லை (துல்லியம்: {confidence*100:.1f}%).\n\n"
                "📸 தயவுசெய்து பாதிக்கப்பட்ட இலையின் தெளிவான புகைப்படத்தை அனுப்பவும்!\n"
                "பாதிப்பு அதிகமாக இருந்தால், உங்கள் அருகிலுள்ள விவசாய அதிகாரியை (KVK) தொடர்பு கொள்ளவும்."
            )
        else:
            low_conf_msg = (
                "⚠️ *Low Diagnostic Confidence*\n\n"
                f"I'm not confident enough about this diagnosis ({confidence*100:.1f}% confidence).\n\n"
                "📸 *Please send a closer, clearer photo of the affected leaf in good daylight!*\n"
                "If the damage is serious, please also show the plant to your local Krishi Vibhag / KVK officer for in-person verification."
            )

        return CropDiagnosis(
            is_crop=True,
            crop_name=crop,
            is_healthy=False,
            condition_name="Low Confidence Detection",
            confidence_score=confidence,
            farmer_friendly_summary=low_conf_msg
        )

    # 3. Retrieve verified guidance from diseases.json
    guidance = get_guidance(raw_class)
    disease_name = guidance["disease"]
    symptoms = guidance.get("symptoms") or "No abnormal symptoms visible."
    actions = guidance.get("immediate_actions", [])
    prevention = guidance.get("prevention", [])
    warning = guidance.get("warning", "")
    source = guidance.get("source", "")
    is_healthy = "healthy" in raw_class.lower()

    # 4. Check localization
    if (is_hi or is_mr or is_ta) and raw_class in TRANSLATIONS:
        target_lang = "mr" if is_mr else ("ta" if is_ta else "hi")
        loc = TRANSLATIONS[raw_class][target_lang]
        disease_name = loc["disease"]
        symptoms = loc["symptoms"]
        actions = loc["actions"]
        prevention = loc["prevention"]
        warning = loc["warning"]

    # 5. Query deterministic government scheme engine
    schemes = find_potentially_relevant_schemes(state=state, crop=crop)

    # 6. Build final WhatsApp formatted message
    summary = build_whatsapp_summary(
        crop=crop,
        disease_name=disease_name,
        confidence=confidence,
        symptoms=symptoms,
        actions=actions,
        prevention=prevention,
        warning=warning,
        source=source,
        schemes=schemes,
        language=language
    )

    return CropDiagnosis(
        is_crop=True,
        crop_name=crop,
        is_healthy=is_healthy,
        condition_name=disease_name,
        confidence_score=confidence,
        symptoms_detected=[symptoms] if symptoms else [],
        treatment=TreatmentPlan(
            cultural=actions,
            organic=[],
            chemical=[]
        ),
        preventive_measures=prevention,
        farmer_friendly_summary=summary
    )


def answer_follow_up(
    last_diagnosis: Optional[CropDiagnosis],
    user_question: str,
    language: str = "en",
    model_name: Optional[str] = None,
    state: str = "All India"
) -> str:
    """
    Answers farmer follow-up questions deterministically from schemes.json and diseases.json.
    Completely zero LLM.
    """
    q = (user_question or "").lower().strip()
    lang = language.lower()
    is_hi = "hi" in lang or "hindi" in lang
    is_mr = "mr" in lang or "marathi" in lang
    is_ta = "ta" in lang or "tamil" in lang

    # 1. Scheme queries (PMFBY, PM-KISAN, MahaDBT, subsidies, insurance, yojana)
    scheme_keywords = ["scheme", "subsidy", "bima", "insurance", "pmfby", "pmkisan", "pm-kisan", "mahadbt", "योजना", "विमा", "अनुदान", "पैसा", "திட்டம்", "மானியம்", "காப்பீடு"]
    if any(k in q for k in scheme_keywords):
        crop = last_diagnosis.crop_name if (last_diagnosis and last_diagnosis.crop_name) else "Tomato"
        schemes = find_potentially_relevant_schemes(state=state, crop=crop)
        
        has_state_schemes = any(s.get("state", "").lower() not in ["all india", "all"] for s in schemes)
        show_central_only = (state and state.lower() != "all india" and not has_state_schemes)
        
        if is_mr:
            lines = [
                "🏛️ *महाराष्ट्र शासन व केंद्र सरकारच्या शेतकरी योजना:*" if not show_central_only else f"ℹ️ *सध्या {state} साठी विशिष्ट योजना उपलब्ध नाहीत. सर्व राज्यांना लागू असलेल्या केंद्र सरकारच्या योजना खालीलप्रमाणे आहेत:*",
                "━━━━━━━━━━━━━━━━━━━━"
            ]
            for s in schemes:
                lines.append(f"👉 *{s['scheme_name']}*")
                lines.append(f"   • वर्गवारी: {s['category']}")
                lines.append(f"   • आवश्यक कागदपत्रे: {', '.join(s['required_documents'])}")
                lines.append(f"   • अर्ज प्रक्रिया: {s['application_process']}")
                lines.append(f"   • अधिकृत संकेतस्थळ: {s['official_source']}")
                if s.get("match_note"):
                    lines.append(f"   ⚠️ टीप: {s['match_note']}")
                lines.append("")
            lines.append("ℹ️ *टीप:* अंतिम पात्रतेसाठी आपल्या गावातील तलाठी/कृषी सहाय्यक किंवा csc केंद्राशी संपर्क साधावा.")
            return "\n".join(lines)

        elif is_hi:
            lines = [
                "🏛️ *किसानों के लिए प्रमुख सरकारी योजनाएं:*" if not show_central_only else f"ℹ️ *वर्तमान में {state} के लिए कोई विशिष्ट योजना नहीं मिली। सभी राज्यों में लागू केंद्र सरकार की योजनाएं इस प्रकार हैं:*",
                "━━━━━━━━━━━━━━━━━━━━"
            ]
            for s in schemes:
                lines.append(f"👉 *{s['scheme_name']}*")
                lines.append(f"   • श्रेणी: {s['category']}")
                lines.append(f"   • आवश्यक दस्तावेज: {', '.join(s['required_documents'])}")
                lines.append(f"   • आवेदन प्रक्रिया: {s['application_process']}")
                lines.append(f"   • आधिकारिक पोर्टल: {s['official_source']}")
                if s.get("match_note"):
                    lines.append(f"   ⚠️ ध्यान दें: {s['match_note']}")
                lines.append("")
            lines.append("ℹ️ *सूचना:* पात्रता की पुष्टि हेतु अपने नजदीकी CSC केंद्र या कृषि कार्यालय से संपर्क करें।")
            return "\n".join(lines)

        elif is_ta:
            lines = [
                "🏛️ *மாநில மற்றும் மத்திய அரசு திட்டங்கள்:*" if not show_central_only else f"ℹ️ *தற்போது {state} க்கான குறிப்பிட்ட திட்டங்கள் எதுவும் இல்லை. அனைத்து மாநிலங்களுக்கும் பொருந்தும் மத்திய அரசு திட்டங்கள் கீழே உள்ளன:*",
                "━━━━━━━━━━━━━━━━━━━━"
            ]
            for s in schemes:
                lines.append(f"👉 *{s['scheme_name']}*")
                lines.append(f"   • வகை: {s['category']}")
                lines.append(f"   • தேவையான ஆவணங்கள்: {', '.join(s['required_documents'])}")
                lines.append(f"   • விண்ணப்பிக்கும் முறை: {s['application_process']}")
                lines.append(f"   • அதிகாரப்பூர்வ தளம்: {s['official_source']}")
                if s.get("match_note"):
                    lines.append(f"   ⚠️ குறிப்பு: {s['match_note']}")
                lines.append("")
            lines.append("ℹ️ *குறிப்பு:* தகுதியை உறுதிப்படுத்த உங்கள் கிராம விவசாய அதிகாரியை அணுகவும்.")
            return "\n".join(lines)

        else:
            lines = [
                "🏛️ *Government Agricultural Schemes & Insurance:*" if not show_central_only else f"ℹ️ *Currently no state-specific schemes found for {state}. Displaying Central Government schemes applicable across India:*",
                "━━━━━━━━━━━━━━━━━━━━"
            ]
            for s in schemes:
                lines.append(f"👉 *{s['scheme_name']}*")
                lines.append(f"   • Category: {s['category']}")
                lines.append(f"   • Required Documents: {', '.join(s['required_documents'])}")
                lines.append(f"   • Application: {s['application_process']}")
                lines.append(f"   • Official Portal: {s['official_source']}")
                if s.get("match_note"):
                    lines.append(f"   ⚠️ Note: {s['match_note']}")
                lines.append("")
            lines.append("ℹ️ *Disclaimer:* These are potentially relevant schemes. Please confirm final eligibility at your local CSC or Krishi Vibhag.")
            return "\n".join(lines)

    # 2. Symptoms, actions, or prevention query for current diagnosis
    if last_diagnosis and last_diagnosis.condition_name:
        cond = last_diagnosis.condition_name
        if any(w in q for w in ["symptom", "sign", "लक्षण", "diye", "identify"]):
            symp = "\n• ".join(last_diagnosis.symptoms_detected) if last_diagnosis.symptoms_detected else "See initial diagnosis summary."
            return f"🔍 *Key Symptoms for {cond}:*\n• {symp}\n\nNeed more help? Consult your local Krishi Vigyan Kendra (KVK)."
        elif any(w in q for w in ["prevent", "बचाव", "काळजी", "stop", "care"]):
            prev = "\n• ".join(last_diagnosis.preventive_measures) if last_diagnosis.preventive_measures else "Ensure crop rotation and avoid overhead watering."
            return f"🛡️ *Preventive Measures for {cond}:*\n• {prev}"
        elif any(w in q for w in ["medicine", "chemical", "spray", "treatment", "दवा", "औषध", "उपचार"]):
            acts = "\n• ".join(last_diagnosis.treatment.cultural) if last_diagnosis.treatment.cultural else "Remove infected leaves and keep foliage dry."
            return f"💊 *Action Plan for {cond}:*\n• {acts}\n\n⚠️ *Important:* Please consult your local Krishi Vibhag or licensed dealer for exact dosage and registered fungicides for your district."

    # 3. Default menu response
    if is_mr:
        return (
            "🌾 *एग्रीडॉक्टर व्हॉट्सअॅप मदत कक्ष* 🌾\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "आपण खालील सेवा वापरू शकता:\n\n"
            "📸 *रोग निदान:* आपल्या पिकाच्या पानाचा स्पष्ट फोटो पाठवा.\n"
            "🏛️ *सरकारी योजना:* 'योजना' किंवा 'विमा' असा मेसेज पाठवून PMFBY आणि PM-KISAN ची माहिती मिळवा.\n"
            "🌐 *भाषा बदला:* 'Hindi', 'Marathi', किंवा 'English' पाठवा.\n\n"
            "कोणतीही शंका असल्यास विचारा!"
        )
    elif is_hi:
        return (
            "🌾 *एग्रीडॉक्टर व्हाट्सएप सहायता* 🌾\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "आप निम्न सेवाएं प्राप्त कर सकते हैं:\n\n"
            "📸 *रोग पहचान:* अपनी फसल या पत्ती की स्पष्ट फोटो भेजें।\n"
            "🏛️ *सरकारी योजनाएं:* 'योजना' या 'बीमा' लिखकर PMFBY और PM-KISAN की जानकारी प्राप्त करें।\n"
            "🌐 *भाषा बदलें:* 'Hindi', 'Marathi', या 'English' भेजें।\n\n"
            "फसल संबंधी कोई भी सवाल पूछ सकते हैं!"
        )
    elif is_ta:
        return (
            "🌾 *KisanGo WhatsApp Assistant* 🌾\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "நான் உங்களுக்கு எப்படி உதவ முடியும்?\n\n"
            "📸 *நோய் கண்டறிதல்:* பாதிக்கப்பட்ட பயிர் இலையின் தெளிவான புகைப்படத்தை அனுப்பவும்.\n"
            "🏛️ *அரசு திட்டங்கள்:* அரசு மானியங்கள் மற்றும் பயிர் காப்பீட்டைப் பார்க்க 'schemes' அல்லது 'PMFBY' எனத் தட்டச்சு செய்யவும்.\n"
            "🌐 *மொழியை மாற்ற:* 'Hindi', 'Marathi', அல்லது 'English' எனப் பதிலளிக்கவும்.\n\n"
            "விவசாயம் சார்ந்த எந்த கேள்வியையும் கேட்க தயங்க வேண்டாம்!"
        )
    else:
        return (
            "🌾 *KisanGo WhatsApp Assistant* 🌾\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "How can I help you today?\n\n"
            "📸 *Disease Diagnosis:* Send a clear photo of your affected crop leaf.\n"
            "🏛️ *Government Schemes:* Type 'schemes' or 'PMFBY' to view available subsidies & crop insurance.\n"
            "🌐 *Change Language:* Reply 'Hindi', 'Marathi', or 'English'.\n\n"
            "Feel free to ask any farming question!"
        )
