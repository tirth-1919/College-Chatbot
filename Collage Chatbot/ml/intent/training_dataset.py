import json
import re
import hashlib
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, UTC
from pathlib import Path
import random
from sqlalchemy.orm import Session
from backend.app.models.entities import MLDataset, AuditLog

class IntentTrainingDataset:
    """
    Controlled ML training dataset for intent classification.
    Provides structured training examples, validation, and reproducibility.
    Ensures no raw student conversations are used directly as training data.
    """

    # AIT-specific intent categories from the original PRD
    INTENT_CATEGORIES = [
        "GREETING",
        "FEE_QUERY",
        "FACULTY_SUBJECT_QUERY",
        "TIMETABLE_QUERY",
        "EXAM_QUERY",
        "RESULT_QUERY",
        "EVENT_IMAGE_SEARCH",
        "EVENT_HISTORY",
        "FACILITY_IMAGE_SEARCH",
        "NOTICE_QUERY",
        "STUDY_ASSISTANT",
        "SYLLABUS_QUERY",
        "SUPPORT_TICKET",
        "SOURCE_REQUEST",
        "GENERAL_EDUCATION",
        "GENERAL_ACADEMIC"
    ]

    # Supported languages for multilingual training
    SUPPORTED_LANGUAGES = ['en', 'hi', 'gu', 'hinglish']

    def __init__(self, dataset_name: str = "ait_intent_classifier"):
        self.dataset_name = dataset_name
        self.dataset_version = "v1.0"
        self.all_examples = []
        self.training_examples = []
        self.train_examples = []
        self.validation_examples = []
        self.test_examples = []
        self.metadata = {
            "created_at": datetime.now(UTC).isoformat(),
            "total_samples": 0,
            "languages": [],
            "intent_distribution": {},
            "is_scrubbed_pii": True,
            "data_source": "controlled_synthetic",
            "reproducibility_seed": 42
        }

    def add_training_example(
        self,
        text: str,
        intent: str,
        language: str = "en",
        entities: Optional[Dict[str, Any]] = None,
        confidence: float = 1.0,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """
        Add a controlled training example.

        Args:
            text: Training text example
            intent: Ground truth intent label
            language: Language code
            entities: Extracted entities (optional)
            confidence: Confidence score for the example
            metadata: Additional metadata
        """
        if intent not in self.INTENT_CATEGORIES:
            raise ValueError(f"Unknown intent: {intent}. Must be one of {self.INTENT_CATEGORIES}")

        if language not in self.SUPPORTED_LANGUAGES:
            raise ValueError(f"Unsupported language: {language}. Must be one of {self.SUPPORTED_LANGUAGES}")

        example = {
            "id": self._generate_example_id(text, intent),
            "text": text,
            "intent": intent,
            "language": language,
            "entities": entities or {},
            "confidence": confidence,
            "metadata": metadata or {},
            "created_at": datetime.now(UTC).isoformat()
        }

        self.training_examples.append(example)
        self.all_examples.append(example)
        self._update_metadata(intent, language)

    def _generate_example_id(self, text: str, intent: str) -> str:
        """Generate deterministic normalized hash for training example to detect duplicates"""
        norm_text = re.sub(r'\s+', ' ', text.strip().lower())
        norm_intent = intent.strip().upper()
        content = f"{norm_text}|{norm_intent}".encode('utf-8')
        return hashlib.sha256(content).hexdigest()[:16]

    def _update_metadata(self, intent: str, language: str):
        """Update dataset metadata"""
        self.metadata["total_samples"] += 1

        if language not in self.metadata["languages"]:
            self.metadata["languages"].append(language)

        self.metadata["intent_distribution"][intent] = \
            self.metadata["intent_distribution"].get(intent, 0) + 1

    def create_balanced_dataset(self, examples_per_intent: int = 20, languages: List[str] = None):
        """
        Create a balanced dataset with equal examples per intent.

        Args:
            examples_per_intent: Number of examples per intent per language
            languages: Languages to include (default: all supported)
        """
        if languages is None:
            languages = self.SUPPORTED_LANGUAGES

        # Controlled synthetic examples for each intent
        synthetic_examples = self._get_synthetic_examples()

        for intent in self.INTENT_CATEGORIES:
            for language in languages:
                # Get language-specific examples
                lang_examples = synthetic_examples.get(intent, {}).get(language, [])

                # Add examples (with some variation)
                for i in range(min(examples_per_intent, len(lang_examples))):
                    example_text = lang_examples[i]
                    self.add_training_example(
                        text=example_text,
                        intent=intent,
                        language=language,
                        confidence=1.0,
                        metadata={"source": "synthetic", "variation": i}
                    )

    def _get_synthetic_examples(self) -> Dict[str, Dict[str, List[str]]]:
        """
        Get controlled synthetic training examples across all 16 intents and 4 languages.
        These are carefully crafted examples, not raw student conversations.
        """
        return {
            "GREETING": {
                "en": [
                    "Hi", "Hello", "Hey", "Good morning", "Good afternoon", "Good evening",
                    "Hi there", "Hello assistant", "Hey bot", "Greetings", "Hello sir", "Hey buddy", "Hi assistant"
                ],
                "hi": [
                    "नमस्ते", "नमस्कार", "प्रणाम", "हेलो", "सुप्रभात", "शुभ संध्या", "नमस्ते सर", "हेलो बॉट", "प्रणाम सर"
                ],
                "gu": [
                    "કેમ છો", "નમસ્તે", "પ્રણામ", "સુપ્રભાત", "જય શ્રી કૃષ્ણ", "હેલો", "કેમ છો સર", "જય માતાજી"
                ],
                "hinglish": [
                    "Kem cho", "Namaste", "Hello ji", "Hey bhai", "Good morning sir", "Kem cho sir", "Hello ait bot"
                ]
            },
            "FEE_QUERY": {
                "en": [
                    "What is the fee for BCA?", "How much is the tuition for BCA?", "BCA fee structure",
                    "Tell me about BCA fees", "What are the charges for BCA course?", "Fee details for BCA program",
                    "How much does BCA cost?", "BCA course fee information", "What is the total fee for BCA?",
                    "BCA admission fee", "BTech fee structure", "MCA fees per semester", "MBA tuition fee details",
                    "What are the fee payment options?", "Fee installment details for college"
                ],
                "hi": [
                    "BCA की फीस क्या है?", "BCA की ट्यूशन फीस कितनी है?", "BCA फीस संरचना",
                    "BCA फीस के बारे में बताएं", "BCA कोर्स के लिए शुल्क क्या है?", "कॉलेज की फीस कितनी है?",
                    "ट्यूशन फीस का विवरण दें", "फीस भरने का तरीका क्या है?"
                ],
                "gu": [
                    "BCA ની ફી શું છે?", "BCA ની ટ્યુશન ફી કેટલી છે?", "BCA ફી સ્ટ્રક્ચર",
                    "BCA ફી વિશે જણાવો", "કોર્સ ફી વિગતો આપો", "કોલેજ ફી કેટલી છે?", "ટ્યુશન ફી ની માહિતી"
                ],
                "hinglish": [
                    "BCA fee kitni hai?", "BCA ki fees kya hai?", "BCA ka fee batao",
                    "BCA course kitni padegi?", "BCA fees ketli che?", "Tuition fees kitni hai?"
                ]
            },
            "FACULTY_SUBJECT_QUERY": {
                "en": [
                    "Who teaches DBMS?", "Which professor handles Python programming?", "Faculty for Data Structures",
                    "Who is the DBMS teacher?", "Python faculty details", "Who teaches database management?",
                    "Data structures professor", "Faculty for OS subject", "Who teaches Java programming?",
                    "Web development professor", "Computer networks faculty name", "Software engineering teacher"
                ],
                "hi": [
                    "DBMS कौन पढ़ाता है?", "Python प्रोग्रामिंग कौन संभालता है?", "Data Structures के लिए फैकल्टी",
                    "DBMS टीचर कौन है?", "Java के प्रोफेसर कौन हैं?", "कंप्यूटर नेटवर्क्स कौन पढ़ाते हैं?"
                ],
                "gu": [
                    "DBMS કોણ ભણાવે છે?", "Python પ્રોગ્રામિંગ કોણ સંભાળે છે?", "Data Structures માટે ફેકલ્ટી",
                    "DBMS ટીચર કોણ છે?", "Java પ્રોફેસર કોણ છે?", "ઓપરેટિંગ સિસ્ટમ કોણ શીખવે છે?"
                ],
                "hinglish": [
                    "DBMS kaun padhata hai?", "Python kon sambhalta hai?", "Data structures faculty kaun hai?",
                    "DBMS na teacher kon che?", "DBMS teacher kon che", "Java professor kaun hai?"
                ]
            },
            "TIMETABLE_QUERY": {
                "en": [
                    "What is today's timetable?", "Show me the class schedule", "Today's class timings",
                    "What are the classes today?", "Timetable for today", "Class schedule for today",
                    "What lectures do we have today?", "BCA semester 3 timetable", "Daily lecture timetable",
                    "Show classroom time table", "When is next class scheduled?"
                ],
                "hi": [
                    "आज का समय सारणी क्या है?", "आज की कक्षा अनुसूची दिखाएं", "आज की क्लास टाइमिंग",
                    "आज कौन से लेक्चर हैं?", "आज का टाइमटेबल क्या है?"
                ],
                "gu": [
                    "આજનો સમયપત્રક શું છે?", "આજની ક્લાસ શેડ્યૂલ બતાવો", "આજની ક્લાસ ટાઇમિંગ",
                    "આજનો ટાઈમટેબલ બતાવો", "આજે કયા લેક્ચર છે?"
                ],
                "hinglish": [
                    "Aaj ka timetable kya hai?", "Today class schedule batao", "Aaj ki classes kya hain?",
                    "Aaj no timetable su che?", "Lecture timetable batao"
                ]
            },
            "EXAM_QUERY": {
                "en": [
                    "When is the exam?", "Exam schedule for this semester", "What are the exam dates?",
                    "Mid-term exam dates", "When are the finals?", "Exam timetable", "Upcoming exams",
                    "When is practical exam?", "Viva exam schedule", "DBMS exam date", "End semester test dates"
                ],
                "hi": [
                    "परीक्षा कब है?", "इस सेमेस्टर की परीक्षा अनुसूची", "परीक्षा की तारीखें क्या हैं?",
                    "मिड टर्म परीक्षा कब होगी?", "परीक्षा का टाइमटेबल दिखाएं"
                ],
                "gu": [
                    "પરીક્ષા ક્યારે છે?", "આ સેમેસ્ટરની પરીક્ષા અનુસૂચી", "પરીક્ષાની તારીખો શું છે?",
                    "મિડ ટર્મ પરીક્ષા તારીખ", "પરીક્ષાનું ટાઈમટેબલ બતાવો"
                ],
                "hinglish": [
                    "Exam kab hai?", "Exam schedule batao", "Pariksha ki dates kya hain?",
                    "DBMS exam kyare che?", "Viva exam date batao"
                ]
            },
            "RESULT_QUERY": {
                "en": [
                    "Show my result", "What is my result?", "Check my SPI and CPI",
                    "How can I see my semester grades?", "Scorecard and marksheet download", "When will GTU results be declared?",
                    "Check semester grades", "Download my scorecard", "View SPI result"
                ],
                "hi": [
                    "मेरा रिजल्ट दिखाएं", "परिणाम कब आएगा?", "मेरे मार्क्स और ग्रेड क्या हैं?",
                    "मार्कशीट कैसे डाउनलोड करें?", "रिजल्ट चेक करें"
                ],
                "gu": [
                    "મારું પરિણામ બતાવો", "રિઝલ્ટ ક્યારે આવશે?", "મારો SPI અને CPI કેટલો છે?",
                    "માર્કશીટ ડાઉનલોડ કરો", "પરિણામ તપાસો"
                ],
                "hinglish": [
                    "Mera result dikhao", "Result kab aayega?", "Marksheet kaise download kare?",
                    "Maro result batavo", "SPI CPI check karo"
                ]
            },
            "EVENT_IMAGE_SEARCH": {
                "en": [
                    "Show me event photos", "Event pictures from last year", "Photos of college events",
                    "Event gallery", "Show me cultural fest photos", "Techfest images",
                    "Annual function pictures", "Hackathon event photos", "Celebration photo album"
                ],
                "hi": [
                    "इवेंट फोटो दिखाएं", "पिछले साल की इवेंट तस्वीरें", "कॉलेज इवेंट की फोटो",
                    "उत्सव की तस्वीरें", "इवेंट गैलरी दिखाएं"
                ],
                "gu": [
                    "ઇવેન્ટ ફોટો બતાવો", "પાછલા વર્ષની ઇવેન્ટ તસવીરો", "કૉલેજ ઇવેન્ટ ની ફોટો",
                    "ફેસ્ટ ફોટો ગેલેરી", "ઇવેન્ટ ચિત્રો"
                ],
                "hinglish": [
                    "Event photos dikhao", "Event pictures batao", "College event ki photos",
                    "Techfest photos dikhao", "Cultural fest pictures"
                ]
            },
            "EVENT_HISTORY": {
                "en": [
                    "What events happened last year?", "Past college events", "History of college events",
                    "Previous year events", "What events were organized?", "List of past fests and hackathons",
                    "Historical events organized in AIT", "What fests took place last year?", "Past activities in AIT college",
                    "History of techfest and cultural events", "Previous year sports events list", "Annual function history"
                ],
                "hi": [
                    "पिछले साल क्या इवेंट हुए?", "पूर्व कॉलेज इवेंट", "कॉलेज इवेंट का इतिहास",
                    "पिछले आयोजनों की सूची", "कॉलेज में पहले कौन से इवेंट हुए थे?", "गत वर्ष के उत्सवों की सूची"
                ],
                "gu": [
                    "પાછલા વર્ષે શું ઇવેન્ટ થયા?", "પૂર્વ કૉલેજ ઇવેન્ટ", "કૉલેજ ઇવેન્ટનો ઇતિહાસ",
                    "અગાઉના કાર્યક્રમો", "ગયા વર્ષે કયા કાર્યક્રમો થયા?", "અગાઉ આયોજિત ઇવેન્ટ્સ"
                ],
                "hinglish": [
                    "Pichle saal kya events hue?", "College events ki history", "Previous year events batao",
                    "Kaya events thaya hata", "Past events ki list batao", "Previous techfest kab hua tha?"
                ]
            },
            "FACILITY_IMAGE_SEARCH": {
                "en": [
                    "Show me library photo", "Smart classroom picture", "Campus images",
                    "Lab photos", "College infrastructure pictures", "Canteen photo",
                    "Computer lab image", "How does campus look?", "Show AIT library photos"
                ],
                "hi": [
                    "लाइब्रेरी की फोटो दिखाएं", "स्मार्ट क्लासरूम की तस्वीर", "कैंपस की तस्वीरें",
                    "कंप्यूटर लैब फोटो", "कैंपस कैसा दिखता है?"
                ],
                "gu": [
                    "લાઇબ્રેરીની ફોટો બતાવો", "સ્માર્ટ ક્લાસરૂમની તસવીર", "કેમ્પસની તસવીરો",
                    "કમ્પ્યુટર લેબ ફોટો", "કેમ્પસ કેવું દેખાય છે?"
                ],
                "hinglish": [
                    "Library photo dikhao", "Smart classroom picture batao", "Campus images dikhao",
                    "Canteen photo batao", "Lab photos dikhao"
                ]
            },
            "NOTICE_QUERY": {
                "en": [
                    "Latest notice", "Show me notices", "College announcements",
                    "Recent circulars", "Academic notices", "Official notice board updates",
                    "New circulars published today", "Check latest college news"
                ],
                "hi": [
                    "नवीनतम नोटिस", "नोटिस दिखाएं", "कॉलेज घोषणाएं", "ताजा परिपत्र", "सूचना पट्ट दिखाएं"
                ],
                "gu": [
                    "તાજેલી નોટિસ", "નોટિસ બતાવો", "કૉલેજ જાહેરાતો", "નવા પરિપત્ર", "સૂચના બોર્ડ બતાવો"
                ],
                "hinglish": [
                    "Latest notice batao", "Notices dikhao", "College announcements",
                    "Taji notice su che?", "Circular update batao"
                ]
            },
            "STUDY_ASSISTANT": {
                "en": [
                    "Help me study", "Quiz questions", "Study plan", "Mock test",
                    "Viva practice", "How can I prepare for viva?", "Flashcards for revision",
                    "Practice questions for exam", "Create revision schedule"
                ],
                "hi": [
                    "पढ़ाई में मदद करें", "क्विज़ प्रश्न", "अध्ययन योजना",
                    "वाइवा की तैयारी कैसे करें?", "मॉक टेस्ट दें"
                ],
                "gu": [
                    "અભ્યાસમાં મદદ કરો", "ક્વિઝ પ્રશ્નો", "અભ્યાસ યોજના",
                    "વાઇવા ની તૈયારી કેવી રીતે કરવી?", "મોક ટેસ્ટ"
                ],
                "hinglish": [
                    "Padhai mein madad karo", "Quiz questions batao", "Study plan banao",
                    "Viva preparation tips", "Mock test prepare karo"
                ]
            },
            "SYLLABUS_QUERY": {
                "en": [
                    "What is DBMS syllabus?", "Give me BCA curriculum", "Course outline for Python",
                    "Show syllabus for semester 3", "What topics are covered in operating systems?",
                    "Download course curriculum", "Subject syllabus modules", "Detailed syllabus for data structures",
                    "Curriculum structure of BCA", "Engineering subject syllabus outline", "Full syllabus for computer science",
                    "What is in BTech computer syllabus?", "Course content of Java programming"
                ],
                "hi": [
                    "DBMS का सिलेबस क्या है?", "BCA पाठ्यक्रम दिखाएं", "कोर्स सिलेबस विवरण",
                    "विषय पाठ्यक्रम डाउनलोड करें", "Python का सिलेबस क्या है?", "डेटा स्ट्रक्चर का पाठ्यक्रम"
                ],
                "gu": [
                    "DBMS નો સિલેબસ શું છે?", "BCA માં શું ભણાવશે?", "અભ્યાસક્રમ બતાવો",
                    "વિષય સિલેબસ ડાઉનલોડ કરો", "Python નો સિલેબસ શું છે?", "સેમેસ્ટર 3 અભ્યાસક્રમ"
                ],
                "hinglish": [
                    "DBMS syllabus kya hai?", "BCA curriculum batao", "Syllabus download kaise kare?",
                    "Syllabus su che?", "Python ka syllabus dikhao", "OS subject syllabus batao"
                ]
            },
            "SOURCE_REQUEST": {
                "en": [
                    "Where did you get this information?", "Show me the source", "Show official website reference",
                    "What is the source citation?", "Give official link", "Provide source citations for this answer",
                    "Where is this verified from?", "What is the source of truth?", "Show verified college reference",
                    "Where did you find this data?", "Official AIT website link", "Cite official document reference"
                ],
                "hi": [
                    "यह जानकारी कहाँ से मिली?", "स्रोत दिखाएं", "आधिकारिक वेबसाइट का लिंक दें",
                    "संदर्भ दिखाएं", "स्रोत का संदर्भ क्या है?", "यह जानकारी कहाँ से ली गई है?"
                ],
                "gu": [
                    "આ માહિતી ક્યાંથી મળી?", "ઓફિશિયલ સોર્સ બતાવો", "વેબસાઇટ લિંક આપો",
                    "સંદર્ભ આપો", "સોર્સ સંદર્ભ શું છે?", "આ માહિતી કઈ વેબસાઇટ પરથી લીધી?"
                ],
                "hinglish": [
                    "Kaha se mila source?", "Official website link dikhao", "Source citation batao",
                    "Source batavo", "Information kaha se aayi?", "Official link do source ki"
                ]
            },
            "SUPPORT_TICKET": {
                "en": [
                    "File a complaint", "Support ticket", "Report an issue",
                    "Helpdesk", "Grievance portal", "Submit grievance ticket", "Report college technical issue",
                    "I have a complaint to register", "File grievance ticket with administration", "Helpdesk support request",
                    "Report a college problem", "Lodge a complaint regarding fees portal"
                ],
                "hi": [
                    "शिकायत दर्ज करें", "सहायता टिकट", "समस्या की रिपोर्ट करें", "शिकायत निवारण",
                    "हेल्पडेस्क टिकट खोलें", "कॉलेज में शिकायत कैसे दर्ज करें?"
                ],
                "gu": [
                    "ફરિયાદ નોંધાવો", "સપોર્ટ ટિકિટ", "સમસ્યાની જાણ કરો", "ફરિયાદ નિવારણ",
                    "હેલ્પડેસ્ક વિનંતી", "કોલેજમાં ફરિયાદ કેવી રીતે કરવી?"
                ],
                "hinglish": [
                    "Complaint register karo", "Support ticket banana hai", "Issue report karo",
                    "Helpdesk ticket open karo", "Complaint karni hai college me", "Support request raise karo"
                ]
            },
            "GENERAL_EDUCATION": {
                "en": [
                    "What is machine learning?", "Explain artificial intelligence", "How does blockchain work?",
                    "Define neural networks", "What is cloud computing?", "Which university is best?",
                    "Compare top engineering colleges", "Explain database normalization theory",
                    "What is object oriented programming?", "Explain recursion in data structures",
                    "What is operating system kernel?", "How does deep learning work?"
                ],
                "hi": [
                    "मशीन लर्निंग क्या है?", "आर्टिफिशियल इंटेलिजेंस समझाएं", "ब्लॉकचेन कैसे काम करता है?",
                    "कौन सा विश्वविद्यालय सबसे अच्छा है?", "क्लाउड कंप्यूटिंग क्या है?", "कंप्यूटर साइंस अवधारणाएं"
                ],
                "gu": [
                    "મશીન લર્નિંગ શું છે?", "આર્ટિફિશિયલ ઇન્ટેલિજન્સ સમજાવો", "બ્લોકચેન કેવી રીતે કામ કરે છે?",
                    "કઈ યુનિવર્સિટી શ્રેષ્ઠ છે?", "ક્લાઉડ કમ્પ્યુટિંગ સમજાવો", "ડેટા સાયન્સ શું છે?"
                ],
                "hinglish": [
                    "Machine learning kya hai?", "AI explain karo", "Blockchain kaise kaam karta hai?",
                    "Which university best hai?", "Cloud computing kya hota hai?", "Neural networks samjhao"
                ]
            },
            "GENERAL_ACADEMIC": {
                "en": [
                    "Help me with my studies", "Explain this concept", "I have an academic question",
                    "Can you help me understand this topic?", "I have a question about college subjects",
                    "Can you assist me with academic doubts?", "General guidance on coursework",
                    "How can I improve my grades?", "Academic doubt clearance", "Academic query regarding college topics",
                    "Doubt in understanding subject theory", "General academic assistance"
                ],
                "hi": [
                    "मेरी पढ़ाई में मदद करें", "इस अवधारणा को समझाएं", "मेरा एक शैक्षणिक प्रश्न है",
                    "क्या आप इस विषय को समझने में मदद कर सकते हैं?", "शैक्षणिक मार्गदर्शन चाहिए",
                    "विषय की थ्योरी समझने में मदद करें"
                ],
                "gu": [
                    "મારા અભ્યાસમાં મને મદદ કરો", "આ ખ્યાલ સમજાવો", "મારો એક શૈક્ષણિક પ્રશ્ન છે",
                    "શું તમે મને આ વિષય સમજવામાં મદદ કરી શકો?", "શૈક્ષણિક માર્ગદર્શન",
                    "વિષય સમજવામાં મદદ કરો"
                ],
                "hinglish": [
                    "Meri studies me help karo", "Yeh topic samjha do", "Academic doubt clear karna hai",
                    "College subjects ke baare me question hai", "Padhai me guide karo", "Theory samjha do"
                ]
            }
        }

    def train_validation_test_split(
        self,
        train_ratio: float = 0.7,
        val_ratio: float = 0.15,
        test_ratio: float = 0.15,
        stratify: bool = True,
        random_seed: int = 42
    ) -> Tuple[List[Dict], List[Dict], List[Dict]]:
        """
        Split dataset into train, validation, and test sets.

        Args:
            train_ratio: Proportion for training set
            val_ratio: Proportion for validation set
            test_ratio: Proportion for test set
            stratify: Whether to stratify by intent
            random_seed: Random seed for reproducibility

        Returns:
            Tuple of (train_set, val_set, test_set)
        """
        if abs(train_ratio + val_ratio + test_ratio - 1.0) > 0.01:
            raise ValueError("Ratios must sum to 1.0")

        random.seed(random_seed)

        source_examples = self.all_examples if self.all_examples else self.training_examples
        if stratify:
            # Stratified split by intent
            train_set, val_set, test_set = [], [], []

            for intent in self.INTENT_CATEGORIES:
                intent_examples = [ex for ex in source_examples if ex["intent"] == intent]
                random.shuffle(intent_examples)

                n = len(intent_examples)
                train_end = int(n * train_ratio)
                val_end = train_end + int(n * val_ratio)

                train_set.extend(intent_examples[:train_end])
                val_set.extend(intent_examples[train_end:val_end])
                test_set.extend(intent_examples[val_end:])
        else:
            # Random split
            all_examples_copy = source_examples.copy()
            random.shuffle(all_examples_copy)

            n = len(all_examples_copy)
            train_end = int(n * train_ratio)
            val_end = train_end + int(n * val_ratio)

            train_set = all_examples_copy[:train_end]
            val_set = all_examples_copy[train_end:val_end]
            test_set = all_examples_copy[val_end:]

        self.train_examples = train_set
        self.training_examples = train_set  # Backwards compatibility
        self.validation_examples = val_set
        self.test_examples = test_set

        return train_set, val_set, test_set

    def validate_dataset(self) -> Dict[str, Any]:
        """
        Validate dataset quality and completeness.

        Returns:
            Dictionary with validation results
        """
        validation_results = {
            "is_valid": True,
            "errors": [],
            "warnings": [],
            "statistics": {}
        }

        # Check minimum samples per intent
        for intent in self.INTENT_CATEGORIES:
            intent_count = len([ex for ex in self.training_examples if ex["intent"] == intent])
            if intent_count < 5:
                validation_results["errors"].append(
                    f"Insufficient samples for intent {intent}: {intent_count} (minimum 5)"
                )
                validation_results["is_valid"] = False
            elif intent_count < 10:
                validation_results["warnings"].append(
                    f"Low sample count for intent {intent}: {intent_count} (recommended 10+)"
                )

        # Check language distribution
        for language in self.SUPPORTED_LANGUAGES:
            lang_count = len([ex for ex in self.training_examples if ex["language"] == language])
            if lang_count == 0:
                validation_results["warnings"].append(f"No samples for language {language}")

        # Check for PII using centralized PIIDetector
        from backend.app.security.pii import PIIDetector
        detector = PIIDetector()
        for example in self.training_examples:
            if detector.is_pii_present(example["text"]):
                validation_results["errors"].append(
                    f"Potential PII found in example {example['id']}: {example['text'][:50]}..."
                )
                validation_results["is_valid"] = False

        # Statistics
        validation_results["statistics"] = {
            "total_samples": len(self.training_examples),
            "intent_distribution": {
                intent: len([ex for ex in self.training_examples if ex["intent"] == intent])
                for intent in self.INTENT_CATEGORIES
            },
            "language_distribution": {
                lang: len([ex for ex in self.training_examples if ex["language"] == lang])
                for lang in self.SUPPORTED_LANGUAGES
            },
            "avg_confidence": sum(ex["confidence"] for ex in self.training_examples) / len(self.training_examples) if self.training_examples else 0
        }

        return validation_results

    def export_dataset(self, file_path: str, format: str = "json"):
        """
        Export dataset to file.

        Args:
            file_path: Path to export file
            format: Export format (json, csv)
        """
        dataset = {
            "metadata": self.metadata,
            "training_examples": self.training_examples,
            "validation_examples": self.validation_examples,
            "test_examples": self.test_examples,
            "intent_categories": self.INTENT_CATEGORIES,
            "supported_languages": self.SUPPORTED_LANGUAGES
        }

        if format == "json":
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(dataset, f, indent=2, ensure_ascii=False)
        else:
            raise ValueError(f"Unsupported format: {format}")

    def save_to_database(self, db: Session) -> MLDataset:
        """
        Save dataset metadata to database.

        Args:
            db: Database session

        Returns:
            MLDataset instance
        """
        # Create dataset record
        dataset = MLDataset(
            name=self.dataset_name,
            task="INTENT_CLASSIFICATION",
            version=self.dataset_version,
            total_samples=len(self.training_examples),
            data_path=None,  # Could be set to file path if exported
            is_scrubbed_pii=self.metadata["is_scrubbed_pii"]
        )

        db.add(dataset)

        # Log audit
        audit = AuditLog(
            actor_role="SYSTEM",
            action="CREATE_ML_DATASET",
            target_entity="MLDataset",
            details={
                "dataset_name": self.dataset_name,
                "version": self.dataset_version,
                "total_samples": len(self.training_examples),
                "intent_categories": self.INTENT_CATEGORIES,
                "languages": self.metadata["languages"]
            }
        )
        db.add(audit)
        db.commit()
        db.refresh(dataset)

        return dataset

    def get_dataset_summary(self) -> Dict[str, Any]:
        """Get summary of the dataset"""
        return {
            "name": self.dataset_name,
            "version": self.dataset_version,
            "total_samples": len(self.training_examples),
            "validation_samples": len(self.validation_examples),
            "test_samples": len(self.test_examples),
            "intent_categories": self.INTENT_CATEGORIES,
            "supported_languages": self.SUPPORTED_LANGUAGES,
            "metadata": self.metadata
        }