# server/aadf/ai_utils.py

import logging
import re
import os
from django.conf import settings
from django.utils import timezone
from django.db.models import Avg, F
from .models import (
    Tender, TenderRequirement, Offer, OfferDocument, Evaluation, EvaluationCriteria
)

logger = logging.getLogger('aadf')

# Try to import optional AI libraries, gracefully handle if not installed
try:
    import nltk
    from nltk.tokenize import word_tokenize
    from nltk.corpus import stopwords
    
    # Download required NLTK resources if not already present
    try:
        nltk.data.find('tokenizers/punkt')
    except LookupError:
        nltk.download('punkt')
    
    try:
        nltk.data.find('corpora/stopwords')
    except LookupError:
        nltk.download('stopwords')
        
    NLTK_AVAILABLE = True
except ImportError:
    NLTK_AVAILABLE = False

try:
    import PyPDF2
    PYPDF_AVAILABLE = True
except ImportError:
    PYPDF_AVAILABLE = False

try:
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.metrics.pairwise import cosine_similarity
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False


def check_missing_requirements(offer):
    """
    Check if an offer is missing any mandatory requirements
    Returns a list of missing requirement descriptions
    """
    if not offer or not offer.tender:
        return []
    
    # Get all mandatory requirements
    mandatory_requirements = TenderRequirement.objects.filter(
        tender=offer.tender,
        is_mandatory=True
    )
    
    # Check which ones are missing
    missing_requirements = []
    for req in mandatory_requirements:
        if not OfferDocument.objects.filter(
            offer=offer,
            document_type=req.document_type
        ).exists():
            missing_requirements.append(req.description)
            
    return missing_requirements


def extract_text_from_pdf(file_path):
    """Extract text content from a PDF file"""
    if not PYPDF_AVAILABLE:
        logger.warning("PyPDF2 not installed, cannot extract text from PDF")
        return ""
    
    try:
        text = ""
        with open(file_path, 'rb') as file:
            reader = PyPDF2.PdfFileReader(file)
            num_pages = reader.numPages
            
            for page_num in range(num_pages):
                page = reader.getPage(page_num)
                text += page.extractText()
                
        return text
    except Exception as e:
        logger.error(f"Error extracting text from PDF: {e}")
        return ""


def analyze_document_completeness(offer_document):
    """
    Analyze how complete a document is based on text content and document type
    Returns a score from 0 to 100 and a list of missing elements
    """
    if not offer_document:
        return 0, ["Document not found"]
    
    # Get document file path
    file_path = os.path.join(settings.MEDIA_ROOT, offer_document.file_path)
    
    # Extract text based on file type
    text = ""
    if file_path.lower().endswith('.pdf') and PYPDF_AVAILABLE:
        text = extract_text_from_pdf(file_path)
    
    # If no text was extracted, return low score
    if not text:
        return 20, ["Could not extract text from document"]
    
    # Basic completeness checks
    word_count = len(text.split())
    if word_count < 100:
        return 30, ["Document appears too short"]
    
    # Check for key sections based on document type
    document_type = offer_document.document_type or ""
    missing_elements = []
    completeness_score = 80  # Default good score
    
    if document_type.lower() == 'technical_proposal':
        # Check for methodology section
        if not re.search(r'methodology|approach|method', text, re.IGNORECASE):
            missing_elements.append("Methodology/Approach section")
            completeness_score -= 15
            
        # Check for timeline/schedule
        if not re.search(r'timeline|schedule|timeframe|deadline', text, re.IGNORECASE):
            missing_elements.append("Timeline/Schedule")
            completeness_score -= 10
            
        # Check for team composition
        if not re.search(r'team|personnel|staff|expert', text, re.IGNORECASE):
            missing_elements.append("Team composition")
            completeness_score -= 10
            
    elif document_type.lower() == 'financial_proposal':
        # Check for budget breakdown
        if not re.search(r'budget|cost|price|amount|sum|total', text, re.IGNORECASE):
            missing_elements.append("Budget breakdown")
            completeness_score -= 25
            
        # Check for payment terms
        if not re.search(r'payment|terms|schedule|installment', text, re.IGNORECASE):
            missing_elements.append("Payment terms")
            completeness_score -= 15
            
    elif document_type.lower() == 'company_profile':
        # Check for company history
        if not re.search(r'history|background|established|founded', text, re.IGNORECASE):
            missing_elements.append("Company history/background")
            completeness_score -= 10
            
        # Check for experience
        if not re.search(r'experience|project|previous|client', text, re.IGNORECASE):
            missing_elements.append("Company experience/previous projects")
            completeness_score -= 15
    
    # Ensure score is within 0-100 range
    completeness_score = max(0, min(completeness_score, 100))
    
    return completeness_score, missing_elements


def suggest_evaluation_score(offer, criteria):
    """
    Suggest an evaluation score for a given offer and criteria
    based on document analysis and historical evaluations
    Returns a suggested score and confidence level
    """
    if not offer or not criteria:
        return None, 0
    
    # Get relevant documents for this offer
    documents = OfferDocument.objects.filter(offer=offer)
    if not documents.exists():
        return None, 0
    
    # Calculate baseline score using historical data
    historical_scores = Evaluation.objects.filter(
        criteria__name=criteria.name,
        criteria__category=criteria.category
    ).exclude(offer=offer)
    
    if historical_scores.exists():
        baseline_score = historical_scores.aggregate(avg_score=Avg('score'))['avg_score']
        if baseline_score is not None:
            baseline_score = round(baseline_score, 2)
        else:
            baseline_score = criteria.max_score * 0.7  # Default to 70% if no historical data
    else:
        baseline_score = criteria.max_score * 0.7  # Default to 70% if no historical data
    
    # Analyze document completeness
    doc_scores = []
    for doc in documents:
        completeness_score, _ = analyze_document_completeness(doc)
        doc_scores.append(completeness_score)
    
    # Calculate document quality factor (0.5-1.5 range)
    avg_doc_score = sum(doc_scores) / len(doc_scores) if doc_scores else 50
    quality_factor = 0.5 + (avg_doc_score / 100)
    
    # Adjust baseline score with quality factor
    suggested_score = baseline_score * quality_factor
    
    # Ensure score is within criteria max_score
    suggested_score = min(suggested_score, criteria.max_score)
    
    # Calculate confidence level (0-100%)
    if historical_scores.count() > 10:
        confidence = 70 + (min(historical_scores.count(), 30) / 30) * 20
    else:
        confidence = 50 + (historical_scores.count() / 10) * 20
        
    # Adjust confidence based on document quality
    confidence = confidence * (avg_doc_score / 100)
    
    # Round for nice display
    suggested_score = round(suggested_score, 2)
    confidence = round(min(confidence, 100), 2)
    
    return suggested_score, confidence


def calculate_document_similarity(doc1, doc2):
    """
    Calculate similarity between two documents
    Returns a similarity score from 0 to 1
    """
    if not SKLEARN_AVAILABLE or not NLTK_AVAILABLE:
        logger.warning("scikit-learn or NLTK not installed, cannot calculate document similarity")
        return 0
    
    # Get document file paths
    file_path1 = os.path.join(settings.MEDIA_ROOT, doc1.file_path)
    file_path2 = os.path.join(settings.MEDIA_ROOT, doc2.file_path)
    
    # Extract text from documents
    text1 = ""
    text2 = ""
    
    if file_path1.lower().endswith('.pdf'):
        text1 = extract_text_from_pdf(file_path1)
    
    if file_path2.lower().endswith('.pdf'):
        text2 = extract_text_from_pdf(file_path2)
    
    if not text1 or not text2:
        return 0
    
    try:
        # Tokenize and clean text
        stop_words = set(stopwords.words('english'))
        
        def preprocess(text):
            tokens = word_tokenize(text.lower())
            filtered_tokens = [w for w in tokens if w.isalnum() and w not in stop_words]
            return ' '.join(filtered_tokens)
            
        processed_text1 = preprocess(text1)
        processed_text2 = preprocess(text2)
        
        # Calculate TF-IDF vectors and similarity
        tfidf_vectorizer = TfidfVectorizer()
        tfidf_matrix = tfidf_vectorizer.fit_transform([processed_text1, processed_text2])
        similarity = cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:2])[0][0]
        
        return float(similarity)
    except Exception as e:
        logger.error(f"Error calculating document similarity: {e}")
        return 0


def analyze_offer_competitiveness(offer):
    """
    Analyze how competitive an offer is compared to others
    Returns a competitiveness score (0-100) and strengths/weaknesses
    """
    if not offer or not offer.tender:
        return 0, [], []
    
    # Get all submitted offers for the same tender
    other_offers = Offer.objects.filter(
        tender=offer.tender,
        status__in=['submitted', 'evaluated', 'awarded']
    ).exclude(id=offer.id)
    
    if not other_offers.exists():
        return 100, ["First submitted offer"], []
    
    strengths = []
    weaknesses = []
    
    # Compare price (if applicable)
    if offer.price and offer.price > 0:
        avg_price = other_offers.filter(price__gt=0).aggregate(avg=Avg('price'))['avg']
        if avg_price:
            if offer.price < avg_price:
                price_diff_percent = round((avg_price - offer.price) / avg_price * 100, 2)
                strengths.append(f"Price is {price_diff_percent}% lower than average")
            else:
                price_diff_percent = round((offer.price - avg_price) / avg_price * 100, 2)
                weaknesses.append(f"Price is {price_diff_percent}% higher than average")
    else:
        weaknesses.append("No price specified")
    
    # Compare technical score (if evaluated)
    if offer.technical_score is not None:
        avg_tech_score = other_offers.filter(
            technical_score__isnull=False
        ).aggregate(avg=Avg('technical_score'))['avg']
        
        if avg_tech_score:
            if offer.technical_score > avg_tech_score:
                strengths.append(f"Technical score is higher than average ({offer.technical_score:.2f} vs {avg_tech_score:.2f})")
            else:
                weaknesses.append(f"Technical score is lower than average ({offer.technical_score:.2f} vs {avg_tech_score:.2f})")
    
    # Calculate document completeness scores
    offer_docs = OfferDocument.objects.filter(offer=offer)
    if offer_docs.exists():
        doc_scores = []
        for doc in offer_docs:
            score, _ = analyze_document_completeness(doc)
            doc_scores.append(score)
        
        avg_doc_score = sum(doc_scores) / len(doc_scores)
        if avg_doc_score > 80:
            strengths.append(f"Documents are very complete (avg score: {avg_doc_score:.2f})")
        elif avg_doc_score < 50:
            weaknesses.append(f"Documents appear incomplete (avg score: {avg_doc_score:.2f})")
    else:
        weaknesses.append("No supporting documents provided")
    
    # Calculate overall competitiveness score
    competitiveness_score = 50  # Default middle score
    
    # Adjust for price competitiveness
    if offer.price and offer.price > 0 and avg_price:
        if offer.price < avg_price:
            competitiveness_score += min(25, price_diff_percent/2)
        else:
            competitiveness_score -= min(25, price_diff_percent/2)
    
    # Adjust for technical score
    if offer.technical_score is not None and avg_tech_score:
        if offer.technical_score > avg_tech_score:
            competitiveness_score += min(25, (offer.technical_score - avg_tech_score)/2)
        else:
            competitiveness_score -= min(25, (avg_tech_score - offer.technical_score)/2)
    
    # Ensure score is within 0-100 range
    competitiveness_score = max(0, min(round(competitiveness_score), 100))
    
    return competitiveness_score, strengths, weaknesses