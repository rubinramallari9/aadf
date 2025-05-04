# server/aadf/ai_analysis.py

import logging
import json
import os
import re
import math
from datetime import datetime, timedelta
from django.conf import settings
from django.db.models import Avg, Count, Q, Sum, Max, Min
from django.utils import timezone

from .models import (
    Tender, Offer, EvaluationCriteria, Evaluation, TenderDocument,
    OfferDocument, Report, User, VendorCompany
)

logger = logging.getLogger('aadf')

# Try to import optional AI libraries
try:
    import numpy as np
    import pandas as pd
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.metrics.pairwise import cosine_similarity
    from sklearn.cluster import KMeans
    AI_LIBS_AVAILABLE = True
except ImportError:
    AI_LIBS_AVAILABLE = False
    logger.warning("Scientific libraries not available. Advanced AI analysis will be limited.")


class AIAnalyzer:
    """Main class for AI analysis of procurement data"""
    
    def __init__(self):
        """Initialize the analyzer"""
        self.ai_libs_available = AI_LIBS_AVAILABLE
    
    def analyze_tender(self, tender_id):
        """Perform comprehensive analysis of a tender"""
        try:
            tender = Tender.objects.get(id=tender_id)
            
            # Get all offers for this tender
            offers = Offer.objects.filter(tender=tender)
            if not offers.exists():
                return {
                    "status": "error",
                    "message": "No offers found for this tender"
                }
            
            # Basic statistics
            basic_stats = self._get_basic_tender_stats(tender, offers)
            
            # Price analysis
            price_analysis = self._analyze_prices(offers)
            
            # Score analysis
            score_analysis = self._analyze_scores(offers)
            
            # Evaluation consistency analysis
            evaluation_consistency = self._analyze_evaluation_consistency(tender)
            
            # Document analysis
            document_analysis = self._analyze_tender_documents(tender)
            
            # Vendor performance analysis
            vendor_analysis = self._analyze_vendor_performance(offers)
            
            # Recommendations
            recommendations = self._generate_tender_recommendations(
                tender, offers, basic_stats, price_analysis, score_analysis
            )
            
            return {
                "status": "success",
                "tender_info": {
                    "id": tender.id,
                    "reference_number": tender.reference_number,
                    "title": tender.title,
                    "status": tender.status
                },
                "basic_stats": basic_stats,
                "price_analysis": price_analysis,
                "score_analysis": score_analysis,
                "evaluation_consistency": evaluation_consistency,
                "document_analysis": document_analysis,
                "vendor_analysis": vendor_analysis,
                "recommendations": recommendations,
                "analysis_timestamp": timezone.now().isoformat()
            }
        except Tender.DoesNotExist:
            return {
                "status": "error",
                "message": f"Tender with ID {tender_id} not found"
            }
        except Exception as e:
            logger.error(f"Error analyzing tender {tender_id}: {str(e)}")
            return {
                "status": "error",
                "message": f"Analysis failed: {str(e)}"
            }
    
    def analyze_offer(self, offer_id):
        """Perform in-depth analysis of a specific offer"""
        try:
            offer = Offer.objects.get(id=offer_id)
            tender = offer.tender
            
            # Get all other offers for this tender for comparison
            other_offers = Offer.objects.filter(tender=tender).exclude(id=offer_id)
            
            # Basic offer information
            offer_info = {
                "id": offer.id,
                "tender_reference": tender.reference_number,
                "vendor_name": offer.vendor.name,
                "status": offer.status,
                "price": float(offer.price) if offer.price else None,
                "technical_score": float(offer.technical_score) if offer.technical_score else None,
                "financial_score": float(offer.financial_score) if offer.financial_score else None,
                "total_score": float(offer.total_score) if offer.total_score else None
            }
            
            # Comparative analysis
            comparative_analysis = self._comparative_offer_analysis(offer, other_offers)
            
            # Document analysis
            document_analysis = self._analyze_offer_documents(offer)
            
            # Compliance analysis
            compliance_analysis = self._offer_compliance_analysis(offer, tender)
            
            # Price competitiveness
            price_analysis = self._analyze_offer_price(offer, other_offers)
            
            # Technical evaluation analysis
            technical_analysis = self._analyze_technical_evaluation(offer)
            
            # Vendor history analysis
            vendor_history = self._analyze_vendor_history(offer.vendor)
            
            # Recommendations
            recommendations = self._generate_offer_recommendations(
                offer, comparative_analysis, compliance_analysis, price_analysis
            )
            
            return {
                "status": "success",
                "offer_info": offer_info,
                "comparative_analysis": comparative_analysis,
                "document_analysis": document_analysis,
                "compliance_analysis": compliance_analysis,
                "price_analysis": price_analysis,
                "technical_analysis": technical_analysis,
                "vendor_history": vendor_history,
                "recommendations": recommendations,
                "analysis_timestamp": timezone.now().isoformat()
            }
        except Offer.DoesNotExist:
            return {
                "status": "error",
                "message": f"Offer with ID {offer_id} not found"
            }
        except Exception as e:
            logger.error(f"Error analyzing offer {offer_id}: {str(e)}")
            return {
                "status": "error",
                "message": f"Analysis failed: {str(e)}"
            }
    
    def generate_evaluation_suggestions(self, offer_id, criteria_id):
        """Generate AI-assisted evaluation suggestions"""
        try:
            offer = Offer.objects.get(id=offer_id)
            criteria = EvaluationCriteria.objects.get(id=criteria_id)
            
            # Check if offer and criteria belong to the same tender
            if criteria.tender.id != offer.tender.id:
                return {
                    "status": "error",
                    "message": "Criteria does not belong to the tender of this offer"
                }
            
            # Get existing evaluations for this criteria from other evaluators
            existing_evaluations = Evaluation.objects.filter(
                offer=offer,
                criteria=criteria
            )
            
            # Get documents to analyze
            documents = OfferDocument.objects.filter(offer=offer)
            
            # Generate suggestion
            suggestion = self._generate_score_suggestion(offer, criteria, existing_evaluations, documents)
            
            return {
                "status": "success",
                "suggestion": suggestion,
                "criteria_info": {
                    "id": criteria.id,
                    "name": criteria.name,
                    "category": criteria.category,
                    "max_score": float(criteria.max_score),
                    "weight": float(criteria.weight)
                },
                "offer_info": {
                    "id": offer.id,
                    "vendor_name": offer.vendor.name
                },
                "existing_evaluations_count": existing_evaluations.count(),
                "analysis_timestamp": timezone.now().isoformat()
            }
        except Offer.DoesNotExist:
            return {
                "status": "error",
                "message": f"Offer with ID {offer_id} not found"
            }
        except EvaluationCriteria.DoesNotExist:
            return {
                "status": "error",
                "message": f"Criteria with ID {criteria_id} not found"
            }
        except Exception as e:
            logger.error(f"Error generating evaluation suggestion: {str(e)}")
            return {
                "status": "error",
                "message": f"Suggestion generation failed: {str(e)}"
            }
    
    def generate_analytics_report(self, tender_id, report_type="comprehensive"):
        """Generate an enhanced analytics report for a tender"""
        try:
            tender = Tender.objects.get(id=tender_id)
            
            # Get all offers and evaluations
            offers = Offer.objects.filter(tender=tender)
            all_evaluations = Evaluation.objects.filter(offer__tender=tender)
            
            if report_type == "comprehensive":
                # Generate comprehensive report with all analyses
                report_data = {
                    "tender_info": {
                        "id": tender.id,
                        "reference_number": tender.reference_number,
                        "title": tender.title,
                        "status": tender.status,
                        "created_at": tender.created_at.isoformat(),
                        "submission_deadline": tender.submission_deadline.isoformat(),
                        "category": tender.category
                    },
                    "executive_summary": self._generate_executive_summary(tender, offers),
                    "performance_metrics": self._generate_performance_metrics(tender, offers),
                    "vendor_analysis": self._generate_vendor_analysis(offers),
                    "evaluation_analysis": self._generate_evaluation_analysis(tender, all_evaluations),
                    "price_analysis": self._generate_price_analysis(offers),
                    "compliance_analysis": self._generate_compliance_analysis(tender, offers),
                    "timeline_analysis": self._generate_timeline_analysis(tender),
                    "anomaly_detection": self._detect_anomalies(tender, offers, all_evaluations),
                    "risk_assessment": self._assess_risks(tender, offers),
                    "recommendations": self._generate_final_recommendations(tender, offers),
                    "report_metadata": {
                        "generated_at": timezone.now().isoformat(),
                        "report_type": report_type,
                        "ai_version": "1.0"
                    }
                }
            elif report_type == "evaluation_focus":
                # Focus on evaluation analysis only
                report_data = {
                    "tender_info": {
                        "id": tender.id,
                        "reference_number": tender.reference_number,
                        "title": tender.title,
                        "status": tender.status
                    },
                    "evaluation_summary": self._generate_evaluation_summary(tender, all_evaluations),
                    "evaluator_consistency": self._analyze_evaluator_consistency(all_evaluations),
                    "criteria_analysis": self._analyze_evaluation_criteria(tender),
                    "score_distribution": self._analyze_score_distribution(all_evaluations),
                    "recommendations": self._generate_evaluation_recommendations(tender, all_evaluations),
                    "report_metadata": {
                        "generated_at": timezone.now().isoformat(),
                        "report_type": report_type,
                        "ai_version": "1.0"
                    }
                }
            elif report_type == "financial_focus":
                # Focus on financial analysis only
                report_data = {
                    "tender_info": {
                        "id": tender.id,
                        "reference_number": tender.reference_number,
                        "title": tender.title,
                        "status": tender.status
                    },
                    "financial_summary": self._generate_financial_summary(tender, offers),
                    "price_analysis": self._analyze_price_details(offers),
                    "market_comparison": self._market_price_comparison(tender, offers),
                    "value_for_money": self._calculate_value_for_money(offers),
                    "budgetary_assessment": self._budgetary_assessment(tender, offers),
                    "financial_recommendations": self._generate_financial_recommendations(tender, offers),
                    "report_metadata": {
                        "generated_at": timezone.now().isoformat(),
                        "report_type": report_type,
                        "ai_version": "1.0"
                    }
                }
            else:
                return {
                    "status": "error",
                    "message": f"Unknown report type: {report_type}"
                }
            
            return {
                "status": "success",
                "report_data": report_data
            }
        except Tender.DoesNotExist:
            return {
                "status": "error",
                "message": f"Tender with ID {tender_id} not found"
            }
        except Exception as e:
            logger.error(f"Error generating analytics report: {str(e)}")
            return {
                "status": "error",
                "message": f"Report generation failed: {str(e)}"
            }
    
    def analyze_vendor_performance(self, vendor_id):
        """Analyze vendor performance across all tenders"""
        try:
            vendor = VendorCompany.objects.get(id=vendor_id)
            
            # Get all offers from this vendor
            offers = Offer.objects.filter(vendor=vendor)
            
            if not offers.exists():
                return {
                    "status": "error",
                    "message": "No offers found for this vendor"
                }
            
            # Basic statistics
            total_offers = offers.count()
            submitted_offers = offers.filter(status__in=['submitted', 'evaluated', 'awarded', 'rejected']).count()
            awarded_offers = offers.filter(status='awarded').count()
            rejected_offers = offers.filter(status='rejected').count()
            
            success_rate = 0
            if submitted_offers > 0:
                success_rate = (awarded_offers / submitted_offers) * 100
            
            # Performance metrics
            avg_technical_score = offers.filter(technical_score__isnull=False).aggregate(
                avg=Avg('technical_score')
            )['avg']
            
            avg_financial_score = offers.filter(financial_score__isnull=False).aggregate(
                avg=Avg('financial_score')
            )['avg']
            
            avg_total_score = offers.filter(total_score__isnull=False).aggregate(
                avg=Avg('total_score')
            )['avg']
            
            # Performance by category
            category_performance = {}
            for offer in offers.filter(tender__category__isnull=False):
                category = offer.tender.category
                if category not in category_performance:
                    category_performance[category] = {
                        'total': 0,
                        'awarded': 0,
                        'avg_score': 0,
                        'scores': []
                    }
                
                category_performance[category]['total'] += 1
                if offer.status == 'awarded':
                    category_performance[category]['awarded'] += 1
                
                if offer.total_score is not None:
                    category_performance[category]['scores'].append(float(offer.total_score))
            
            # Calculate averages for each category
            for category, data in category_performance.items():
                if data['scores']:
                    data['avg_score'] = sum(data['scores']) / len(data['scores'])
                del data['scores']  # Remove the raw scores from the output
            
            # Trend analysis over time
            time_performance = self._analyze_vendor_time_performance(vendor, offers)
            
            # Competitive analysis
            competitive_analysis = self._analyze_vendor_competitiveness(vendor, offers)
            
            # Compliance analysis
            compliance_analysis = self._analyze_vendor_compliance(vendor, offers)
            
            # Strengths and weaknesses
            strengths_weaknesses = self._identify_vendor_strengths_weaknesses(vendor, offers)
            
            # Recommendations
            recommendations = self._generate_vendor_recommendations(vendor, offers)
            
            return {
                "status": "success",
                "vendor_info": {
                    "id": vendor.id,
                    "name": vendor.name,
                    "registration_number": vendor.registration_number,
                },
                "basic_stats": {
                    "total_offers": total_offers,
                    "submitted_offers": submitted_offers,
                    "awarded_offers": awarded_offers,
                    "rejected_offers": rejected_offers,
                    "success_rate": success_rate
                },
                "performance_metrics": {
                    "avg_technical_score": avg_technical_score,
                    "avg_financial_score": avg_financial_score,
                    "avg_total_score": avg_total_score,
                },
                "category_performance": category_performance,
                "time_performance": time_performance,
                "competitive_analysis": competitive_analysis,
                "compliance_analysis": compliance_analysis,
                "strengths_weaknesses": strengths_weaknesses,
                "recommendations": recommendations,
                "analysis_timestamp": timezone.now().isoformat()
            }
        except VendorCompany.DoesNotExist:
            return {
                "status": "error",
                "message": f"Vendor with ID {vendor_id} not found"
            }
        except Exception as e:
            logger.error(f"Error analyzing vendor performance: {str(e)}")
            return {
                "status": "error",
                "message": f"Analysis failed: {str(e)}"
            }
    
    def detect_evaluation_anomalies(self, tender_id):
        """Detect anomalies in tender evaluations"""
        try:
            tender = Tender.objects.get(id=tender_id)
            evaluations = Evaluation.objects.filter(offer__tender=tender)
            
            if not evaluations.exists():
                return {
                    "status": "error",
                    "message": "No evaluations found for this tender"
                }
            
            # Group evaluations by criteria and offer
            grouped_evaluations = {}
            for evaluation in evaluations:
                offer_id = evaluation.offer.id
                criteria_id = evaluation.criteria.id
                
                key = f"{offer_id}_{criteria_id}"
                if key not in grouped_evaluations:
                    grouped_evaluations[key] = []
                
                grouped_evaluations[key].append({
                    'id': evaluation.id,
                    'evaluator': evaluation.evaluator.username,
                    'score': float(evaluation.score),
                    'max_score': float(evaluation.criteria.max_score)
                })
            
            # Detect anomalies
            anomalies = []
            for key, evals in grouped_evaluations.items():
                if len(evals) < 2:
                    continue  # Need at least 2 evaluations to detect anomalies
                
                scores = [e['score'] for e in evals]
                avg_score = sum(scores) / len(scores)
                
                # Calculate standard deviation
                variance = sum((score - avg_score) ** 2 for score in scores) / len(scores)
                std_dev = math.sqrt(variance)
                
                # Check for outliers (>2 standard deviations from mean)
                for eval_info in evals:
                    z_score = abs(eval_info['score'] - avg_score) / (std_dev if std_dev > 0 else 1)
                    if z_score > 2:
                        offer_id, criteria_id = map(int, key.split('_'))
                        offer = Offer.objects.get(id=offer_id)
                        criteria = EvaluationCriteria.objects.get(id=criteria_id)
                        
                        anomalies.append({
                            'evaluation_id': eval_info['id'],
                            'offer_id': offer_id,
                            'vendor_name': offer.vendor.name,
                            'criteria_id': criteria_id,
                            'criteria_name': criteria.name,
                            'evaluator': eval_info['evaluator'],
                            'score': eval_info['score'],
                            'average_score': avg_score,
                            'deviation': z_score,
                            'severity': 'high' if z_score > 3 else 'medium',
                            'normalized_score': eval_info['score'] / eval_info['max_score'] * 100
                        })
            
            # Detect evaluator bias
            evaluator_bias = self._detect_evaluator_bias(evaluations)
            
            return {
                "status": "success",
                "tender_info": {
                    "id": tender.id,
                    "reference_number": tender.reference_number,
                    "title": tender.title
                },
                "anomalies": sorted(anomalies, key=lambda x: x['deviation'], reverse=True),
                "evaluator_bias": evaluator_bias,
                "total_evaluations": evaluations.count(),
                "anomalies_count": len(anomalies),
                "analysis_timestamp": timezone.now().isoformat()
            }
        except Tender.DoesNotExist:
            return {
                "status": "error",
                "message": f"Tender with ID {tender_id} not found"
            }
        except Exception as e:
            logger.error(f"Error detecting evaluation anomalies: {str(e)}")
            return {
                "status": "error",
                "message": f"Anomaly detection failed: {str(e)}"
            }
    
    # Helper methods for analysis
    def _get_basic_tender_stats(self, tender, offers):
        """Get basic statistics for a tender"""
        total_offers = offers.count()
        submitted_offers = offers.filter(status__in=['submitted', 'evaluated', 'awarded', 'rejected']).count()
        draft_offers = offers.filter(status='draft').count()
        avg_price = offers.filter(price__isnull=False).aggregate(avg=Avg('price'))['avg']
        min_price = offers.filter(price__isnull=False).aggregate(min=Min('price'))['min']
        max_price = offers.filter(price__isnull=False).aggregate(max=Max('price'))['max']
        
        return {
            "total_offers": total_offers,
            "submitted_offers": submitted_offers,
            "draft_offers": draft_offers,
            "avg_price": float(avg_price) if avg_price is not None else None,
            "min_price": float(min_price) if min_price is not None else None,
            "max_price": float(max_price) if max_price is not None else None,
            "price_spread_percentage": (
                ((max_price - min_price) / min_price) * 100
                if min_price is not None and max_price is not None and min_price > 0
                else None
            )
        }
    
    def _analyze_prices(self, offers):
        """Analyze prices of offers"""
        valid_prices = [float(offer.price) for offer in offers if offer.price is not None]
        
        if not valid_prices:
            return {
                "analysis_performed": False,
                "reason": "No valid prices found"
            }
            
        avg_price = sum(valid_prices) / len(valid_prices)
        median_price = sorted(valid_prices)[len(valid_prices) // 2]
        price_variance = sum((price - avg_price) ** 2 for price in valid_prices) / len(valid_prices)
        std_dev = math.sqrt(price_variance)
        
        # Detect outliers (>2 standard deviations from mean)
        outliers = []
        for offer in offers:
            if offer.price is not None:
                price = float(offer.price)
                z_score = abs(price - avg_price) / (std_dev if std_dev > 0 else 1)
                if z_score > 2:
                    outliers.append({
                        "vendor_name": offer.vendor.name,
                        "offer_id": offer.id,
                        "price": price,
                        "z_score": z_score,
                        "status": offer.status
                    })
        
        # Analyze price clustering
        clusters = self._cluster_prices(valid_prices)
        
        return {
            "analysis_performed": True,
            "avg_price": avg_price,
            "median_price": median_price,
            "standard_deviation": std_dev,
            "price_variance": price_variance,
            "coefficient_of_variation": (std_dev / avg_price) * 100 if avg_price > 0 else 0,
            "price_range": max(valid_prices) - min(valid_prices),
            "price_outliers": sorted(outliers, key=lambda x: x['z_score'], reverse=True),
            "price_clusters": clusters
        }
    
    def _cluster_prices(self, prices):
        """Cluster prices using statistical methods"""
        if len(prices) < 2:
            return {
                "clustering_performed": False,
                "reason": "Not enough prices for clustering"
            }
            
        # Simple implementation without sklearn
        # Just group prices within 10% of each other
        clusters = []
        remaining_prices = prices.copy()
        
        while remaining_prices:
            center = remaining_prices[0]
            cluster = [center]
            remaining_prices.remove(center)
            
            i = 0
            while i < len(remaining_prices):
                price = remaining_prices[i]
                if abs(price - center) / center <= 0.1:  # Within 10%
                    cluster.append(price)
                    remaining_prices.pop(i)
                else:
                    i += 1
            
            clusters.append({
                "center": sum(cluster) / len(cluster),
                "min": min(cluster),
                "max": max(cluster),
                "count": len(cluster)
            })
        
        return {
            "clustering_performed": True,
            "clusters": sorted(clusters, key=lambda x: x['count'], reverse=True),
            "cluster_count": len(clusters)
        }
    
    def _analyze_scores(self, offers):
        """Analyze evaluation scores"""
        offers_with_scores = offers.filter(
            technical_score__isnull=False,
            financial_score__isnull=False,
            total_score__isnull=False
        )
        
        if not offers_with_scores.exists():
            return {
                "analysis_performed": False,
                "reason": "No offers with complete scores found"
            }
        
        # Calculate average scores
        avg_technical = offers_with_scores.aggregate(avg=Avg('technical_score'))['avg']
        avg_financial = offers_with_scores.aggregate(avg=Avg('financial_score'))['avg']
        avg_total = offers_with_scores.aggregate(avg=Avg('total_score'))['avg']
        
        # Calculate score spreads
        technical_scores = [float(o.technical_score) for o in offers_with_scores]
        financial_scores = [float(o.financial_score) for o in offers_with_scores]
        total_scores = [float(o.total_score) for o in offers_with_scores]
        
        technical_spread = max(technical_scores) - min(technical_scores)
        financial_spread = max(financial_scores) - min(financial_scores)
        total_spread = max(total_scores) - min(total_scores)
        
        # Identify top scoring offers
        top_offers = offers_with_scores.order_by('-total_score')[:3].values(
            'id', 'vendor__name', 'technical_score', 'financial_score', 'total_score'
        )
        
        return {
            "analysis_performed": True,
            "score_averages": {
                "technical": float(avg_technical),
                "financial": float(avg_financial),
                "total": float(avg_total)
            },
            "score_spreads": {
                "technical": technical_spread,
                "financial": financial_spread,
                "total": total_spread
            },
            "top_offers": list(top_offers),
            "score_distribution": {
                "very_high": offers_with_scores.filter(total_score__gte=90).count(),
                "high": offers_with_scores.filter(total_score__lt=90, total_score__gte=80).count(),
                "medium": offers_with_scores.filter(total_score__lt=80, total_score__gte=70).count(),
                "low": offers_with_scores.filter(total_score__lt=70).count()
            }
        }
    
    def _analyze_evaluation_consistency(self, tender):
        """Analyze consistency among evaluators"""
        # Get all evaluations for this tender
        evaluations = Evaluation.objects.filter(offer__tender=tender)
        if not evaluations.exists():
            return {
                "analysis_performed": False,
                "reason": "No evaluations found"
            }
            
        # Group by offer and criteria
        consistency_data = []
        for offer in Offer.objects.filter(tender=tender):
            for criteria in EvaluationCriteria.objects.filter(tender=tender):
                # Get all evaluations for this offer and criteria
                offer_criteria_evals = evaluations.filter(
                    offer=offer,
                    criteria=criteria
                )
                
                if offer_criteria_evals.count() >= 2:
                    # Calculate statistics
                    scores = [float(e.score) for e in offer_criteria_evals]
                    avg_score = sum(scores) / len(scores)
                    max_score = max(scores)
                    min_score = min(scores)
                    variance = sum((score - avg_score) ** 2 for score in scores) / len(scores)
                    
                    # Only include if there's significant variance
                    if variance > 0:
                        consistency_data.append({
                            "offer_id": offer.id,
                            "vendor_name": offer.vendor.name,
                            "criteria_id": criteria.id,
                            "criteria_name": criteria.name,
                            "evaluator_count": offer_criteria_evals.count(),
                            "avg_score": avg_score,
                            "max_score": max_score,
                            "min_score": min_score,
                            "score_range": max_score - min_score,
                            "variance": variance,
                            "std_deviation": math.sqrt(variance)
                        })
        
        # Sort by variance (highest first)
        consistency_data.sort(key=lambda x: x['variance'], reverse=True)
        
        # Calculate overall consistency metrics
        overall_variance = 0
        total_data_points = 0
        
        for data in consistency_data:
            overall_variance += data['variance']
            total_data_points += 1
            
        avg_variance = overall_variance / total_data_points if total_data_points > 0 else 0
            
        return {
            "analysis_performed": True,
            "consistency_issues": consistency_data[:5],  # Top 5 inconsistencies
            "total_consistency_issues": len(consistency_data),
            "overall_consistency": {
                "average_variance": avg_variance,
                "consistency_rating": self._get_consistency_rating(avg_variance)
            }
        }
    
    def _get_consistency_rating(self, variance):
        """Get a qualitative rating for evaluation consistency"""
        if variance < 5:
            return "Excellent"
        elif variance < 10:
            return "Good"
        elif variance < 15:
            return "Moderate"
        elif variance < 25:
            return "Poor"
        else:
            return "Very Poor"
    
    def _analyze_tender_documents(self, tender):
        """Analyze tender documents"""
        documents = TenderDocument.objects.filter(tender=tender)
        
        if not documents.exists():
            return {
                "analysis_performed": False,
                "reason": "No documents found"
            }
            
        document_count = documents.count()
        document_types = {}
        
        for doc in documents:
            doc_type = doc.mime_type or "unknown"
            if doc_type in document_types:
                document_types[doc_type] += 1
            else:
                document_types[doc_type] = 1
        
        # Size analysis
        total_size = sum(doc.file_size or 0 for doc in documents)
        avg_size = total_size / document_count if document_count > 0 else 0
        
        return {
            "analysis_performed": True,
            "document_count": document_count,
            "document_types": document_types,
            "size_analysis": {
                "total_size_kb": total_size / 1024 if total_size else 0,
                "avg_size_kb": avg_size / 1024 if avg_size else 0
            }
        }
    
    def _analyze_vendor_performance(self, offers):
        """Analyze performance of vendors in a tender"""
        vendors = {}
        for offer in offers:
            vendor_id = offer.vendor.id
            if vendor_id not in vendors:
                vendors[vendor_id] = {
                    "vendor_id": vendor_id,
                    "vendor_name": offer.vendor.name,
                    "offer_id": offer.id,
                    "offer_status": offer.status,
                    "price": float(offer.price) if offer.price else None,
                    "technical_score": float(offer.technical_score) if offer.technical_score else None,
                    "financial_score": float(offer.financial_score) if offer.financial_score else None,
                    "total_score": float(offer.total_score) if offer.total_score else None,
                    "has_previous_tenders": False,
                    "previous_awarded_count": 0,
                    "avg_previous_score": None
                }
                
                # Check vendor history
                previous_offers = Offer.objects.filter(
                    vendor_id=vendor_id
                ).exclude(
                    id=offer.id
                )
                
                if previous_offers.exists():
                    vendors[vendor_id]["has_previous_tenders"] = True
                    vendors[vendor_id]["previous_awarded_count"] = previous_offers.filter(
                        status='awarded'
                    ).count()
                    
                    avg_score = previous_offers.filter(
                        total_score__isnull=False
                    ).aggregate(
                        avg=Avg('total_score')
                    )['avg']
                    
                    vendors[vendor_id]["avg_previous_score"] = float(avg_score) if avg_score else None
        
        return {
            "analysis_performed": True,
            "vendor_data": list(vendors.values())
        }
    
    def _generate_tender_recommendations(self, tender, offers, basic_stats, price_analysis, score_analysis):
        """Generate recommendations based on tender analysis"""
        recommendations = []
        
        # Check if there are enough offers
        if basic_stats["submitted_offers"] < 3:
            recommendations.append({
                "type": "warning",
                "issue": "Limited competition",
                "description": "There are fewer than 3 submitted offers, which may limit competitive pricing.",
                "suggested_action": "Consider extending submission deadline or reaching out to more potential vendors."
            })
        
        # Check for price anomalies
        if price_analysis.get("analysis_performed", False):
            price_outliers = price_analysis.get("price_outliers", [])
            if price_outliers:
                recommendations.append({
                    "type": "info",
                    "issue": "Price anomalies detected",
                    "description": f"There are {len(price_outliers)} offers with unusual pricing compared to others.",
                    "suggested_action": "Review pricing carefully for these offers to ensure they are realistic and competitive."
                })
            
            # Check price spread
            if basic_stats.get("price_spread_percentage", 0) and basic_stats["price_spread_percentage"] > 40:
                recommendations.append({
                    "type": "warning",
                    "issue": "High price variation",
                    "description": f"Price spread is {basic_stats['price_spread_percentage']:.1f}%, indicating significant variation in offers.",
                    "suggested_action": "Verify that all vendors understood requirements correctly and are offering comparable solutions."
                })
        
        # Check for evaluation consistency issues
        evaluation_consistency = self._analyze_evaluation_consistency(tender)
        if evaluation_consistency.get("analysis_performed", False):
            consistency_issues = evaluation_consistency.get("consistency_issues", [])
            if consistency_issues:
                recommendations.append({
                    "type": "warning",
                    "issue": "Evaluation inconsistency",
                    "description": "There are significant variations in how evaluators scored certain offers.",
                    "suggested_action": "Review evaluation criteria and consider a calibration session for evaluators."
                })
        
        # Procurement process recommendations
        if tender.status == 'closed':
            days_since_closing = (timezone.now() - tender.updated_at).days
            if days_since_closing > 14 and not offers.filter(status='awarded').exists():
                recommendations.append({
                    "type": "warning",
                    "issue": "Delayed award decision",
                    "description": f"Tender has been closed for {days_since_closing} days without an award decision.",
                    "suggested_action": "Accelerate the evaluation process to maintain vendor interest and meet project timelines."
                })
        
        # Document-based recommendations
        documents = TenderDocument.objects.filter(tender=tender)
        if documents.count() < 3:
            recommendations.append({
                "type": "info",
                "issue": "Limited documentation",
                "description": "The tender has relatively few supporting documents.",
                "suggested_action": "Consider adding more detailed specifications or requirements to help vendors."
            })
            
        return recommendations
    
    def _comparative_offer_analysis(self, offer, other_offers):
        """Compare an offer against others in the same tender"""
        if not other_offers.exists():
            return {
                "analysis_performed": False,
                "reason": "No other offers to compare with"
            }
            
        # Price comparison
        prices = [float(o.price) for o in other_offers if o.price is not None]
        if offer.price is not None and prices:
            avg_price = sum(prices) / len(prices)
            price_diff = float(offer.price) - avg_price
            price_diff_percent = (price_diff / avg_price) * 100
            price_rank = 1
            for other_price in prices:
                if offer.price > other_price:
                    price_rank += 1
        else:
            avg_price = None
            price_diff = None
            price_diff_percent = None
            price_rank = None
        
        # Score comparison
        if offer.total_score is not None:
            scores = [float(o.total_score) for o in other_offers if o.total_score is not None]
            if scores:
                avg_score = sum(scores) / len(scores)
                score_diff = float(offer.total_score) - avg_score
                score_rank = 1
                for other_score in scores:
                    if offer.total_score < other_score:
                        score_rank += 1
            else:
                avg_score = None
                score_diff = None
                score_rank = None
        else:
            avg_score = None
            score_diff = None
            score_rank = None
            
        return {
            "analysis_performed": True,
            "comparison_count": other_offers.count(),
            "price_comparison": {
                "offer_price": float(offer.price) if offer.price else None,
                "avg_other_price": avg_price,
                "price_difference": price_diff,
                "price_difference_percent": price_diff_percent,
                "price_rank": price_rank,
                "price_competitiveness": self._get_price_competitiveness_rating(price_diff_percent) if price_diff_percent is not None else None
            },
            "score_comparison": {
                "offer_score": float(offer.total_score) if offer.total_score else None,
                "avg_other_score": avg_score,
                "score_difference": score_diff,
                "score_rank": score_rank,
                "relative_performance": self._get_score_performance_rating(score_diff) if score_diff is not None else None
            }
        }
    
    def _get_price_competitiveness_rating(self, price_diff_percent):
        """Get a qualitative rating for price competitiveness"""
        if price_diff_percent < -15:
            return "Highly Competitive"
        elif price_diff_percent < -5:
            return "Competitive"
        elif price_diff_percent < 5:
            return "Average"
        elif price_diff_percent < 15:
            return "Less Competitive"
        else:
            return "Not Competitive"
    
    def _get_score_performance_rating(self, score_diff):
        """Get a qualitative rating for score performance"""
        if score_diff > 15:
            return "Exceptional"
        elif score_diff > 5:
            return "Above Average"
        elif score_diff > -5:
            return "Average"
        elif score_diff > -15:
            return "Below Average"
        else:
            return "Poor"
    
    def _analyze_offer_documents(self, offer):
        """Analyze documents submitted with an offer"""
        documents = OfferDocument.objects.filter(offer=offer)
        
        if not documents.exists():
            return {
                "analysis_performed": False,
                "reason": "No documents found"
            }
            
        document_count = documents.count()
        document_types = {}
        
        for doc in documents:
            doc_type = doc.document_type or doc.mime_type or "unknown"
            if doc_type in document_types:
                document_types[doc_type] += 1
            else:
                document_types[doc_type] = 1
        
        # Size analysis
        total_size = sum(doc.file_size or 0 for doc in documents)
        avg_size = total_size / document_count if document_count > 0 else 0
        
        # Missing documents
        required_docs = offer.tender.requirements.filter(is_mandatory=True).count()
        submitted_required = 0
        
        for req in offer.tender.requirements.filter(is_mandatory=True):
            if documents.filter(document_type=req.document_type).exists():
                submitted_required += 1
        
        return {
            "analysis_performed": True,
            "document_count": document_count,
            "document_types": document_types,
            "size_analysis": {
                "total_size_kb": total_size / 1024 if total_size else 0,
                "avg_size_kb": avg_size / 1024 if avg_size else 0
            },
            "compliance": {
                "required_docs": required_docs,
                "submitted_required": submitted_required,
                "missing_required": required_docs - submitted_required,
                "compliance_rate": (submitted_required / required_docs * 100) if required_docs > 0 else 100
            }
        }
    
    def _offer_compliance_analysis(self, offer, tender):
        """Analyze offer compliance with tender requirements"""
        requirements = tender.requirements.all()
        documents = OfferDocument.objects.filter(offer=offer)
        
        if not requirements.exists():
            return {
                "analysis_performed": False,
                "reason": "No defined requirements found"
            }
            
        total_requirements = requirements.count()
        mandatory_requirements = requirements.filter(is_mandatory=True).count()
        
        compliant_requirements = 0
        compliant_mandatory = 0
        missing_docs = []
        
        for req in requirements:
            if documents.filter(document_type=req.document_type).exists():
                compliant_requirements += 1
                if req.is_mandatory:
                    compliant_mandatory += 1
            elif req.is_mandatory:
                missing_docs.append({
                    "requirement_id": req.id,
                    "description": req.description,
                    "document_type": req.document_type
                })
        
        return {
            "analysis_performed": True,
            "total_requirements": total_requirements,
            "mandatory_requirements": mandatory_requirements,
            "compliant_requirements": compliant_requirements,
            "compliant_mandatory": compliant_mandatory,
            "overall_compliance_rate": (compliant_requirements / total_requirements * 100) if total_requirements > 0 else 100,
            "mandatory_compliance_rate": (compliant_mandatory / mandatory_requirements * 100) if mandatory_requirements > 0 else 100,
            "missing_mandatory_docs": missing_docs,
            "compliance_rating": self._get_compliance_rating(
                compliant_mandatory, 
                mandatory_requirements
            )
        }
    
    def _get_compliance_rating(self, compliant, total):
        """Get a qualitative rating for compliance"""
        if total == 0:
            return "Fully Compliant"
            
        rate = compliant / total * 100
        
        if rate >= 100:
            return "Fully Compliant"
        elif rate >= 90:
            return "Mostly Compliant"
        elif rate >= 75:
            return "Partially Compliant"
        elif rate >= 50:
            return "Marginally Compliant"
        else:
            return "Non-Compliant"
    
    def _analyze_offer_price(self, offer, other_offers):
        """Analyze the price of an offer"""
        if offer.price is None:
            return {
                "analysis_performed": False,
                "reason": "No price specified for this offer"
            }
            
        if not other_offers.filter(price__isnull=False).exists():
            return {
                "analysis_performed": False,
                "reason": "No other offers with prices to compare"
            }
            
        offer_price = float(offer.price)
        other_prices = [float(o.price) for o in other_offers if o.price is not None]
        
        avg_price = sum(other_prices) / len(other_prices)
        median_price = sorted(other_prices)[len(other_prices) // 2]
        min_price = min(other_prices)
        max_price = max(other_prices)
        
        # Calculate percentile
        sorted_prices = sorted(other_prices + [offer_price])
        percentile = sorted_prices.index(offer_price) / len(sorted_prices) * 100
        
        # Calculate z-score
        std_dev = math.sqrt(sum((p - avg_price) ** 2 for p in other_prices) / len(other_prices))
        z_score = (offer_price - avg_price) / std_dev if std_dev > 0 else 0
        
        # Differential from average
        diff_from_avg = offer_price - avg_price
        diff_percentage = (diff_from_avg / avg_price) * 100 if avg_price > 0 else 0
        
        return {
            "analysis_performed": True,
            "offer_price": offer_price,
            "market_metrics": {
                "average_price": avg_price,
                "median_price": median_price,
                "min_price": min_price,
                "max_price": max_price,
                "price_spread": max_price - min_price
            },
            "competitiveness": {
                "price_percentile": percentile,
                "z_score": z_score,
                "differential": diff_from_avg,
                "differential_percentage": diff_percentage,
                "is_lowest": offer_price <= min_price,
                "is_highest": offer_price >= max_price
            },
            "price_rating": self._get_price_rating(diff_percentage, percentile)
        }
    
    def _get_price_rating(self, diff_percentage, percentile):
        """Get a qualitative rating for price"""
        if diff_percentage < -15:
            return "Highly Competitive"
        elif diff_percentage < -5:
            return "Competitive"
        elif diff_percentage < 5:
            return "Average"
        elif diff_percentage < 15:
            return "Less Competitive"
        else:
            return "Not Competitive"
    
    def _analyze_technical_evaluation(self, offer):
        """Analyze technical evaluation of an offer"""
        if offer.technical_score is None:
            return {
                "analysis_performed": False,
                "reason": "No technical score available"
            }
            
        # Get evaluations by criteria
        evaluations = Evaluation.objects.filter(offer=offer)
        
        if not evaluations.exists():
            return {
                "analysis_performed": False,
                "reason": "No detailed evaluations found"
            }
            
        criteria_scores = {}
        for eval_item in evaluations:
            criteria_id = eval_item.criteria.id
            if criteria_id not in criteria_scores:
                criteria_scores[criteria_id] = {
                    "criteria_id": criteria_id,
                    "criteria_name": eval_item.criteria.name,
                    "criteria_category": eval_item.criteria.category,
                    "max_score": float(eval_item.criteria.max_score),
                    "weight": float(eval_item.criteria.weight),
                    "evaluations": []
                }
                
            criteria_scores[criteria_id]["evaluations"].append({
                "evaluator": eval_item.evaluator.username,
                "score": float(eval_item.score),
                "comment": eval_item.comment
            })
        
        # Calculate average scores per criteria
        for criteria_id, data in criteria_scores.items():
            scores = [e["score"] for e in data["evaluations"]]
            avg_score = sum(scores) / len(scores)
            normalized_score = avg_score / data["max_score"] * 100 if data["max_score"] > 0 else 0
            
            data["avg_score"] = avg_score
            data["normalized_score"] = normalized_score
            data["score_variance"] = sum((s - avg_score) ** 2 for s in scores) / len(scores) if len(scores) > 1 else 0
        
        # Identify strengths and weaknesses
        strengths = []
        weaknesses = []
        
        for criteria_id, data in criteria_scores.items():
            if data["normalized_score"] >= 80:
                strengths.append({
                    "criteria_id": criteria_id,
                    "criteria_name": data["criteria_name"],
                    "normalized_score": data["normalized_score"]
                })
            elif data["normalized_score"] <= 60:
                weaknesses.append({
                    "criteria_id": criteria_id,
                    "criteria_name": data["criteria_name"],
                    "normalized_score": data["normalized_score"]
                })
                
        # Sort strengths and weaknesses
        strengths.sort(key=lambda x: x["normalized_score"], reverse=True)
        weaknesses.sort(key=lambda x: x["normalized_score"])
        
        return {
            "analysis_performed": True,
            "technical_score": float(offer.technical_score),
            "criteria_scores": list(criteria_scores.values()),
            "strengths": strengths[:3],  # Top 3 strengths
            "weaknesses": weaknesses[:3],  # Top 3 weaknesses
            "evaluation_count": evaluations.count(),
            "evaluator_count": evaluations.values('evaluator').distinct().count()
        }
    
    def _analyze_vendor_history(self, vendor):
        """Analyze vendor history across all tenders"""
        # Get all past offers from this vendor (excluding the current one)
        past_offers = Offer.objects.filter(
            vendor=vendor,
            status__in=['submitted', 'evaluated', 'awarded', 'rejected']
        )
        
        if not past_offers.exists():
            return {
                "analysis_performed": False,
                "reason": "No historical data available for this vendor"
            }
            
        # Calculate historical metrics
        total_offers = past_offers.count()
        awarded_offers = past_offers.filter(status='awarded').count()
        rejected_offers = past_offers.filter(status='rejected').count()
        success_rate = (awarded_offers / total_offers) * 100 if total_offers > 0 else 0
        
        # Average scores
        avg_technical = past_offers.filter(technical_score__isnull=False).aggregate(
            avg=Avg('technical_score')
        )['avg']
        
        avg_financial = past_offers.filter(financial_score__isnull=False).aggregate(
            avg=Avg('financial_score')
        )['avg']
        
        avg_total = past_offers.filter(total_score__isnull=False).aggregate(
            avg=Avg('total_score')
        )['avg']
        
        # Performance by category
        categories = {}
        for offer in past_offers.filter(tender__category__isnull=False):
            category = offer.tender.category
            if category not in categories:
                categories[category] = {
                    'total': 0,
                    'awarded': 0
                }
                
            categories[category]['total'] += 1
            if offer.status == 'awarded':
                categories[category]['awarded'] += 1
                
        for category, data in categories.items():
            data['success_rate'] = (data['awarded'] / data['total']) * 100 if data['total'] > 0 else 0
            
        # Performance trend
        trend_data = []
        for offer in past_offers.filter(total_score__isnull=False).order_by('created_at'):
            trend_data.append({
                'date': offer.created_at.strftime('%Y-%m-%d'),
                'tender_reference': offer.tender.reference_number,
                'status': offer.status,
                'total_score': float(offer.total_score)
            })
            
        return {
            "analysis_performed": True,
            "historical_metrics": {
                "total_offers": total_offers,
                "awarded_offers": awarded_offers,
                "rejected_offers": rejected_offers,
                "success_rate": success_rate
            },
            "historical_scores": {
                "avg_technical_score": float(avg_technical) if avg_technical else None,
                "avg_financial_score": float(avg_financial) if avg_financial else None,
                "avg_total_score": float(avg_total) if avg_total else None
            },
            "category_performance": categories,
            "performance_trend": trend_data,
            "vendor_rating": self._get_vendor_rating(success_rate, avg_total)
        }
    
    def _get_vendor_rating(self, success_rate, avg_score):
        """Get a qualitative rating for vendor performance"""
        # Convert avg_score to a 0-100 scale if needed
        normalized_score = float(avg_score) if avg_score else 0
        if normalized_score > 0 and normalized_score <= 10:
            normalized_score *= 10  # Assuming it was on a 0-10 scale
            
        # Weighted calculation (60% success rate, 40% avg score)
        performance_score = 0.6 * success_rate + 0.4 * normalized_score
        
        if performance_score >= 85:
            return "Excellent"
        elif performance_score >= 75:
            return "Very Good"
        elif performance_score >= 65:
            return "Good"
        elif performance_score >= 50:
            return "Average"
        else:
            return "Below Average"
    
    def _generate_offer_recommendations(self, offer, comparative_analysis, compliance_analysis, price_analysis):
        """Generate recommendations based on offer analysis"""
        recommendations = []
        
        # Check compliance issues
        if compliance_analysis.get("analysis_performed", False):
            missing_docs = compliance_analysis.get("missing_mandatory_docs", [])
            if missing_docs:
                recommendations.append({
                    "type": "warning",
                    "issue": "Missing required documents",
                    "description": f"There are {len(missing_docs)} mandatory documents missing from this offer.",
                    "suggested_action": "Request the missing documents from the vendor before proceeding with evaluation."
                })
                
        # Check price issues
        if price_analysis.get("analysis_performed", False):
            price_rating = price_analysis.get("price_rating")
            
            if price_rating == "Not Competitive":
                recommendations.append({
                    "type": "warning",
                    "issue": "Non-competitive pricing",
                    "description": "This offer's price is significantly higher than other offers.",
                    "suggested_action": "Verify if there are special features or quality aspects that justify the premium pricing."
                })
            elif price_rating == "Highly Competitive" and offer.price and float(offer.price) > 0:
                recommendations.append({
                    "type": "info",
                    "issue": "Unusually low pricing",
                    "description": "This offer's price is significantly lower than other offers.",
                    "suggested_action": "Verify if all requirements are understood and can be met at this price point."
                })
                
        # Check score issues
        if offer.technical_score is not None and float(offer.technical_score) < 60:
            recommendations.append({
                "type": "warning",
                "issue": "Low technical score",
                "description": "This offer received a relatively low technical evaluation score.",
                "suggested_action": "Review specific evaluation criteria to identify major weaknesses."
            })
            
        # Check for evaluation inconsistency
        evaluations = Evaluation.objects.filter(offer=offer)
        if evaluations.count() >= 2:
            # Calculate variance in scores
            criteria_variances = {}
            for eval_item in evaluations:
                criteria_id = eval_item.criteria.id
                criteria_name = eval_item.criteria.name
                if criteria_id not in criteria_variances:
                    criteria_variances[criteria_id] = {
                        "name": criteria_name,
                        "scores": []
                    }
                    
                criteria_variances[criteria_id]["scores"].append(float(eval_item.score))
                
            # Find criteria with high variance
            high_variance_criteria = []
            for criteria_id, data in criteria_variances.items():
                if len(data["scores"]) >= 2:
                    avg = sum(data["scores"]) / len(data["scores"])
                    variance = sum((s - avg) ** 2 for s in data["scores"]) / len(data["scores"])
                    if variance > 25:  # Arbitrary threshold
                        high_variance_criteria.append({
                            "criteria_id": criteria_id,
                            "criteria_name": data["name"],
                            "variance": variance
                        })
                        
            if high_variance_criteria:
                recommendations.append({
                    "type": "warning",
                    "issue": "Inconsistent evaluations",
                    "description": f"Found {len(high_variance_criteria)} criteria with significantly inconsistent evaluation scores.",
                    "suggested_action": "Review these criteria to ensure consistent evaluation standards."
                })
                
        return recommendations
    
    def _generate_score_suggestion(self, offer, criteria, existing_evaluations, documents):
        """Generate a suggested score for a specific criteria"""
        # Start with a default suggestion
        suggestion = {
            "suggested_score": 0,
            "confidence": 0,
            "suggested_score_percentage": 0,
            "max_score": float(criteria.max_score),
            "explanation": "",
            "factors": []
        }
        
        # Factor 1: Existing evaluations from other evaluators
        if existing_evaluations.exists():
            # Use average of existing evaluations as a starting point
            existing_scores = [float(e.score) for e in existing_evaluations]
            avg_score = sum(existing_scores) / len(existing_scores)
            
            suggestion["factors"].append({
                "factor": "Existing evaluations",
                "impact": "High",
                "description": f"Based on {len(existing_scores)} existing evaluations with average score {avg_score:.2f}",
                "weight": 0.5
            })
            
            base_score = avg_score
            confidence = 0.6  # Higher confidence due to existing evaluations
        else:
            # No existing evaluations
            # Use vendor historical performance as a basis
            vendor_performance = self._analyze_vendor_history(offer.vendor)
            
            if vendor_performance.get("analysis_performed", False):
                # Calculate a baseline score based on historical performance
                avg_score = vendor_performance.get("historical_scores", {}).get("avg_total_score")
                
                if avg_score is not None:
                    # Convert to the criteria's scale
                    avg_score_percentage = min(avg_score, 100) / 100  # Ensure it's 0-100
                    base_score = avg_score_percentage * criteria.max_score
                    
                    suggestion["factors"].append({
                        "factor": "Vendor historical performance",
                        "impact": "Medium",
                        "description": f"Based on vendor's historical average score of {avg_score:.2f}%",
                        "weight": 0.3
                    })
                    
                    confidence = 0.3
                else:
                    # No historical scores available
                    base_score = criteria.max_score * 0.7  # Default to 70%
                    confidence = 0.2
                    
                    suggestion["factors"].append({
                        "factor": "Default baseline",
                        "impact": "Low",
                        "description": "No historical data available, using default baseline score",
                        "weight": 0.2
                    })
            else:
                # No historical data
                base_score = criteria.max_score * 0.7  # Default to 70%
                confidence = 0.2
                
                suggestion["factors"].append({
                    "factor": "Default baseline",
                    "impact": "Low",
                    "description": "No historical data available, using default baseline score",
                    "weight": 0.2
                })
        
        # Factor 2: Document completeness for this criteria
        if criteria.category == 'technical':
            # Check if there are relevant documents for this criteria
            relevant_docs = documents.filter(document_type__icontains=criteria.name)
            
            if relevant_docs.exists():
                suggestion["factors"].append({
                    "factor": "Document submission",
                    "impact": "Medium",
                    "description": f"Found {relevant_docs.count()} documents relevant to this criteria",
                    "weight": 0.2
                })
                
                # Adjust score up slightly
                base_score = min(base_score * 1.1, criteria.max_score)
                confidence += 0.1
            else:
                suggestion["factors"].append({
                    "factor": "Document submission",
                    "impact": "Low",
                    "description": "No documents specifically related to this criteria found",
                    "weight": 0.1
                })
                
                # Adjust score down slightly
                base_score = base_score * 0.9
                
        # Factor 3: Compliance with requirements
        compliance_analysis = self._offer_compliance_analysis(offer, offer.tender)
        
        if compliance_analysis.get("analysis_performed", False):
            compliance_rate = compliance_analysis.get("mandatory_compliance_rate", 0)
            
            suggestion["factors"].append({
                "factor": "Compliance with requirements",
                "impact": "High" if compliance_rate < 100 else "Medium",
                "description": f"Offer has {compliance_rate:.1f}% compliance with mandatory requirements",
                "weight": 0.3
            })
            
            # Adjust score based on compliance
            if compliance_rate < 100:
                # Penalize for non-compliance
                compliance_factor = (compliance_rate / 100) ** 2  # Square to emphasize penalty
                base_score = base_score * compliance_factor
                # Lower confidence for non-compliant offers
                confidence -= 0.1
            else:
                # Slight boost for full compliance
                base_score = min(base_score * 1.05, criteria.max_score)
                confidence += 0.1
        
        # Calculate final suggested score
        suggested_score = min(round(base_score, 2), criteria.max_score)
        suggested_score_percentage = (suggested_score / criteria.max_score) * 100
        
        # Generate explanation
        explanation_parts = []
        for factor in suggestion["factors"]:
            explanation_parts.append(f"{factor['factor']} ({factor['impact']} impact): {factor['description']}")
            
        explanation = " ".join(explanation_parts)
        
        # Set the final values
        suggestion["suggested_score"] = suggested_score
        suggestion["confidence"] = min(confidence, 0.95)  # Cap confidence at 95%
        suggestion["suggested_score_percentage"] = suggested_score_percentage
        suggestion["explanation"] = explanation
        
        return suggestion
    
    def _generate_executive_summary(self, tender, offers):
        """Generate an executive summary for a tender analysis report"""
        # Basic tender information
        tender_info = f"This tender ({tender.reference_number}: {tender.title}) "
        
        # Status information
        if tender.status == 'draft':
            tender_info += "is currently in draft status and has not been published yet."
        elif tender.status == 'published':
            tender_info += f"is currently published with submission deadline on {tender.submission_deadline.strftime('%Y-%m-%d')}."
        elif tender.status == 'closed':
            tender_info += "is closed and awaiting award decision."
        elif tender.status == 'awarded':
            awarded_offer = offers.filter(status='awarded').first()
            if awarded_offer:
                tender_info += f"has been awarded to {awarded_offer.vendor.name}."
            else:
                tender_info += "has been marked as awarded, but no specific offer is marked as awarded."
        
        # Offer information
        offer_info = ""
        if offers.exists():
            submitted_count = offers.filter(status__in=['submitted', 'evaluated', 'awarded', 'rejected']).count()
            if submitted_count > 0:
                offer_info = f"The tender received {submitted_count} submitted offers"
                
                # Price range if available
                valid_prices = [o.price for o in offers if o.price is not None]
                if valid_prices:
                    min_price = min(valid_prices)
                    max_price = max(valid_prices)
                    price_range = (max_price - min_price) / min_price * 100 if min_price > 0 else 0
                    
                    if price_range > 30:
                        offer_info += f" with a wide price range (variation of {price_range:.1f}%)."
                    else:
                        offer_info += f" with a relatively tight price range (variation of {price_range:.1f}%)."
                else:
                    offer_info += "."
                    
                # Add score information if available
                scored_offers = offers.filter(total_score__isnull=False)
                if scored_offers.exists():
                    avg_score = scored_offers.aggregate(avg=Avg('total_score'))['avg']
                    offer_info += f" The average total score across evaluated offers is {avg_score:.2f}."
            else:
                offer_info = "No offers have been submitted for this tender yet."
        else:
            offer_info = "No offers have been received for this tender yet."
        
        # Key findings and recommendations
        key_findings = "Key findings: "
        recommendation_items = []
        
        # Check competition level
        if offers.count() < 3:
            key_findings += "Limited competition with few offers received. "
            recommendation_items.append("Consider extending the submission deadline or reaching out to more potential vendors")
        
        # Check price variation
        valid_prices = [float(o.price) for o in offers if o.price is not None]
        if valid_prices and len(valid_prices) >= 2:
            price_variance = sum((p - sum(valid_prices)/len(valid_prices)) ** 2 for p in valid_prices) / len(valid_prices)
            if price_variance > 1000000:  # Arbitrary threshold
                key_findings += "High price variation among offers. "
                recommendation_items.append("Verify that all vendors understood requirements correctly")
        
        # Check evaluation consistency
        evaluations = Evaluation.objects.filter(offer__tender=tender)
        if evaluations.exists():
            eval_consistency = self._analyze_evaluation_consistency(tender)
            if eval_consistency.get("analysis_performed", False) and eval_consistency.get("consistency_issues", []):
                key_findings += "Inconsistent evaluation scores across evaluators. "
                recommendation_items.append("Review evaluation criteria with evaluators to ensure consistent standards")
        
        # Format recommendations
        recommendations = "Recommendations: "
        if recommendation_items:
            recommendations += "; ".join(recommendation_items) + "."
        else:
            recommendations += "No specific recommendations at this time."
        
        return {
            "tender_overview": tender_info,
            "offer_summary": offer_info,
            "key_findings": key_findings,
            "recommendations": recommendations
        }
    
    def _generate_performance_metrics(self, tender, offers):
        """Generate performance metrics for a tender"""
        # Basic statistics
        total_offers = offers.count()
        submitted_offers = offers.filter(status__in=['submitted', 'evaluated', 'awarded', 'rejected']).count()
        
        # Competition metrics
        competition_level = "Low"
        if submitted_offers >= 5:
            competition_level = "High"
        elif submitted_offers >= 3:
            competition_level = "Medium"
            
        # Price metrics
        price_metrics = {}
        valid_prices = [float(o.price) for o in offers if o.price is not None]
        if valid_prices:
            avg_price = sum(valid_prices) / len(valid_prices)
            min_price = min(valid_prices)
            max_price = max(valid_prices)
            price_spread = max_price - min_price
            price_spread_percentage = (price_spread / min_price) * 100 if min_price > 0 else 0
            
            price_metrics = {
                "average_price": avg_price,
                "min_price": min_price,
                "max_price": max_price,
                "price_spread": price_spread,
                "price_spread_percentage": price_spread_percentage,
                "price_consistency": "High" if price_spread_percentage < 20 else "Medium" if price_spread_percentage < 40 else "Low"
            }
            
        # Evaluation metrics
        evaluation_metrics = {}
        evaluations = Evaluation.objects.filter(offer__tender=tender)
        if evaluations.exists():
            total_evaluations = evaluations.count()
            evaluators_count = evaluations.values('evaluator').distinct().count()
            avg_score = evaluations.aggregate(avg=Avg('score'))['avg']
            
            # Calculate evaluation consistency
            criteria_variances = {}
            for e in evaluations:
                offer_id = e.offer.id
                criteria_id = e.criteria.id
                key = f"{offer_id}_{criteria_id}"
                
                if key not in criteria_variances:
                    criteria_variances[key] = []
                    
                criteria_variances[key].append(float(e.score))
            
            # Calculate average variance
            total_variance = 0
            variance_count = 0
            
            for scores in criteria_variances.values():
                if len(scores) >= 2:
                    avg = sum(scores) / len(scores)
                    variance = sum((s - avg) ** 2 for s in scores) / len(scores)
                    total_variance += variance
                    variance_count += 1
                    
            avg_variance = total_variance / variance_count if variance_count > 0 else 0
            consistency_rating = self._get_consistency_rating(avg_variance)
            
            evaluation_metrics = {
                "total_evaluations": total_evaluations,
                "evaluators_count": evaluators_count,
                "average_score": float(avg_score) if avg_score else None,
                "average_variance": avg_variance,
                "consistency_rating": consistency_rating
            }
            
        # Timeline metrics
        timeline_metrics = {}
        if tender.published_at and tender.submission_deadline:
            submission_period_days = (tender.submission_deadline - tender.published_at).days
            timeline_metrics["submission_period_days"] = submission_period_days
            
        if tender.status == 'awarded' and tender.published_at:
            award_period_days = (tender.updated_at - tender.published_at).days
            timeline_metrics["total_process_days"] = award_period_days
            
        return {
            "basic_metrics": {
                "total_offers": total_offers,
                "submitted_offers": submitted_offers,
                "competition_level": competition_level
            },
            "price_metrics": price_metrics,
            "evaluation_metrics": evaluation_metrics,
            "timeline_metrics": timeline_metrics
        }
    
    def _generate_vendor_analysis(self, offers):
        """Generate vendor analysis for a tender report"""
        if not offers.exists():
            return {
                "analysis_performed": False,
                "reason": "No offers available for analysis"
            }
            
        # Analyze each vendor
        vendor_analysis = []
        for offer in offers:
            vendor = offer.vendor
            
            # Get vendor history
            vendor_history = self._analyze_vendor_history(vendor)
            
            # Get offer performance
            offer_data = {
                "vendor_id": vendor.id,
                "vendor_name": vendor.name,
                "offer_id": offer.id,
                "offer_status": offer.status,
                "price": float(offer.price) if offer.price else None,
                "technical_score": float(offer.technical_score) if offer.technical_score else None,
                "financial_score": float(offer.financial_score) if offer.financial_score else None,
                "total_score": float(offer.total_score) if offer.total_score else None
            }
            
            # Add historical data if available
            if vendor_history.get("analysis_performed", False):
                historical_data = {
                    "previous_tenders_count": vendor_history.get("historical_metrics", {}).get("total_offers", 0),
                    "previous_success_rate": vendor_history.get("historical_metrics", {}).get("success_rate", 0),
                    "historical_avg_score": vendor_history.get("historical_scores", {}).get("avg_total_score"),
                    "vendor_rating": vendor_history.get("vendor_rating")
                }
                
                offer_data.update(historical_data)
            
            vendor_analysis.append(offer_data)
            
        # Sort by total score (if available)
        vendor_analysis.sort(
            key=lambda x: x.get("total_score", 0) if x.get("total_score") is not None else 0, 
            reverse=True
        )
        
        return {
            "analysis_performed": True,
            "vendor_data": vendor_analysis,
            "vendor_count": len(vendor_analysis)
        }
    
    def _generate_evaluation_analysis(self, tender, evaluations):
        """Generate evaluation analysis for a tender report"""
        if not evaluations.exists():
            return {
                "analysis_performed": False,
                "reason": "No evaluations available for analysis"
            }
            
        # Analysis by criteria
        criteria_analysis = {}
        for evaluation in evaluations:
            criteria_id = evaluation.criteria.id
            
            if criteria_id not in criteria_analysis:
                criteria_analysis[criteria_id] = {
                    "criteria_id": criteria_id,
                    "criteria_name": evaluation.criteria.name,
                    "criteria_category": evaluation.criteria.category,
                    "max_score": float(evaluation.criteria.max_score),
                    "weight": float(evaluation.criteria.weight),
                    "scores": []
                }
                
            criteria_analysis[criteria_id]["scores"].append(float(evaluation.score))
            
        # Calculate statistics for each criteria
        for criteria_id, data in criteria_analysis.items():
            scores = data["scores"]
            avg_score = sum(scores) / len(scores)
            normalized_score = avg_score / data["max_score"] * 100 if data["max_score"] > 0 else 0
            
            variance = sum((s - avg_score) ** 2 for s in scores) / len(scores) if len(scores) > 1 else 0
            std_dev = math.sqrt(variance)
            
            data["avg_score"] = avg_score
            data["normalized_score"] = normalized_score
            data["variance"] = variance
            data["std_deviation"] = std_dev
            data["sample_count"] = len(scores)
            del data["scores"]  # Remove raw scores from output
            
        # Analysis by evaluator
        evaluator_analysis = {}
        for evaluation in evaluations:
            evaluator_id = evaluation.evaluator.id
            
            if evaluator_id not in evaluator_analysis:
                evaluator_analysis[evaluator_id] = {
                    "evaluator_id": evaluator_id,
                    "evaluator_name": evaluation.evaluator.username,
                    "evaluation_count": 0,
                    "avg_score": 0,
                    "avg_normalized_score": 0,
                    "scores": [],
                    "normalized_scores": []
                }
                
            evaluator_analysis[evaluator_id]["evaluation_count"] += 1
            score = float(evaluation.score)
            max_score = float(evaluation.criteria.max_score)
            normalized_score = (score / max_score) * 100 if max_score > 0 else 0
            
            evaluator_analysis[evaluator_id]["scores"].append(score)
            evaluator_analysis[evaluator_id]["normalized_scores"].append(normalized_score)
            
        # Calculate evaluator statistics
        for evaluator_id, data in evaluator_analysis.items():
            data["avg_score"] = sum(data["scores"]) / len(data["scores"]) if data["scores"] else 0
            data["avg_normalized_score"] = sum(data["normalized_scores"]) / len(data["normalized_scores"]) if data["normalized_scores"] else 0
            data["score_variance"] = sum((s - data["avg_score"]) ** 2 for s in data["scores"]) / len(data["scores"]) if len(data["scores"]) > 1 else 0
            
            del data["scores"]
            del data["normalized_scores"]
            
        # Sort criteria by weight
        criteria_list = list(criteria_analysis.values())
        criteria_list.sort(key=lambda x: x["weight"], reverse=True)
        
        # Identify criteria with high variance
        high_variance_criteria = [c for c in criteria_list if c["variance"] > 25]  # Arbitrary threshold
        
        # Identify evaluators with bias
        evaluator_list = list(evaluator_analysis.values())
        avg_normalized_scores = [e["avg_normalized_score"] for e in evaluator_list]
        overall_avg = sum(avg_normalized_scores) / len(avg_normalized_scores) if avg_normalized_scores else 0
        
        biased_evaluators = []
        for evaluator in evaluator_list:
            score_diff = evaluator["avg_normalized_score"] - overall_avg
            if abs(score_diff) > 15:  # Arbitrary threshold
                bias_type = "lenient" if score_diff > 0 else "strict"
                biased_evaluators.append({
                    "evaluator_id": evaluator["evaluator_id"],
                    "evaluator_name": evaluator["evaluator_name"],
                    "bias_type": bias_type,
                    "score_difference": score_diff
                })
                
        return {
            "analysis_performed": True,
            "evaluation_count": evaluations.count(),
            "evaluator_count": len(evaluator_analysis),
            "criteria_count": len(criteria_analysis),
            "criteria_analysis": criteria_list,
            "evaluator_analysis": evaluator_list,
            "high_variance_criteria": high_variance_criteria,
            "biased_evaluators": biased_evaluators
        }
    
    def _generate_price_analysis(self, offers):
        """Generate price analysis for a tender report"""
        # Filter offers with valid prices
        valid_offers = [o for o in offers if o.price is not None]
        
        if not valid_offers:
            return {
                "analysis_performed": False,
                "reason": "No offers with valid prices available for analysis"
            }
            
        # Extract prices
        prices = [float(o.price) for o in valid_offers]
        
        # Basic statistics
        avg_price = sum(prices) / len(prices)
        min_price = min(prices)
        max_price = max(prices)
        median_price = sorted(prices)[len(prices) // 2]
        
        # Price spread
        price_range = max_price - min_price
        price_range_percentage = (price_range / min_price) * 100 if min_price > 0 else 0
        
        # Variance and standard deviation
        variance = sum((p - avg_price) ** 2 for p in prices) / len(prices)
        std_dev = math.sqrt(variance)
        coef_variation = (std_dev / avg_price) * 100 if avg_price > 0 else 0
        
        # Detect outliers
        outliers = []
        for offer in valid_offers:
            price = float(offer.price)
            z_score = abs(price - avg_price) / std_dev if std_dev > 0 else 0
            
            if z_score > 2:
                outliers.append({
                    "offer_id": offer.id,
                    "vendor_name": offer.vendor.name,
                    "price": price,
                    "z_score": z_score,
                    "deviation_percentage": ((price - avg_price) / avg_price) * 100
                })
                
        # Price clusters
        clusters = self._cluster_prices(prices)
        
        # Price distribution
        price_distribution = {
            "very_low": len([p for p in prices if p < avg_price * 0.8]),
            "low": len([p for p in prices if p >= avg_price * 0.8 and p < avg_price * 0.95]),
            "average": len([p for p in prices if p >= avg_price * 0.95 and p <= avg_price * 1.05]),
            "high": len([p for p in prices if p > avg_price * 1.05 and p <= avg_price * 1.2]),
            "very_high": len([p for p in prices if p > avg_price * 1.2])
        }
        
        return {
            "analysis_performed": True,
            "offers_analyzed": len(valid_offers),
            "basic_statistics": {
                "average_price": avg_price,
                "median_price": median_price,
                "min_price": min_price,
                "max_price": max_price,
                "price_range": price_range,
                "price_range_percentage": (price_range / min_price) * 100 if min_price > 0 else 0
            },
            "statistical_analysis": {
                "variance": variance,
                "standard_deviation": std_dev,
                "coefficient_of_variation": coef_variation
            },
            "price_outliers": outliers,
            "price_clustering": clusters,
            "price_distribution": price_distribution
        }
    
    def _generate_compliance_analysis(self, tender, offers):
        """Generate compliance analysis for a tender report"""
        requirements = tender.requirements.all()
        
        if not requirements.exists():
            return {
                "analysis_performed": False,
                "reason": "No requirements defined for this tender"
            }
            
        # Analyze each offer's compliance
        compliance_data = []
        for offer in offers.filter(status__in=['submitted', 'evaluated', 'awarded', 'rejected']):
            compliance = self._offer_compliance_analysis(offer, tender)
            
            if compliance.get("analysis_performed", False):
                compliance_data.append({
                    "offer_id": offer.id,
                    "vendor_name": offer.vendor.name,
                    "total_requirements": compliance.get("total_requirements", 0),
                    "compliant_requirements": compliance.get("compliant_requirements", 0),
                    "mandatory_requirements": compliance.get("mandatory_requirements", 0),
                    "compliant_mandatory": compliance.get("compliant_mandatory", 0),
                    "overall_compliance_rate": compliance.get("overall_compliance_rate", 0),
                    "mandatory_compliance_rate": compliance.get("mandatory_compliance_rate", 0),
                    "compliance_rating": compliance.get("compliance_rating", "Unknown"),
                    "missing_mandatory_count": len(compliance.get("missing_mandatory_docs", []))
                })
                
        # Calculate overall compliance statistics
        avg_compliance = sum(d["overall_compliance_rate"] for d in compliance_data) / len(compliance_data) if compliance_data else 0
        avg_mandatory_compliance = sum(d["mandatory_compliance_rate"] for d in compliance_data) / len(compliance_data) if compliance_data else 0
        
        # Find common missing requirements
        requirement_compliance = {}
        for req in requirements:
            requirement_compliance[req.id] = {
                "requirement_id": req.id,
                "description": req.description,
                "document_type": req.document_type,
                "is_mandatory": req.is_mandatory,
                "compliance_count": 0,
                "total_offers": len(offers.filter(status__in=['submitted', 'evaluated', 'awarded', 'rejected']))
            }
            
        for offer in offers.filter(status__in=['submitted', 'evaluated', 'awarded', 'rejected']):
            documents = OfferDocument.objects.filter(offer=offer)
            
            for req in requirements:
                if documents.filter(document_type=req.document_type).exists():
                    requirement_compliance[req.id]["compliance_count"] += 1
                    
        # Calculate compliance rates for each requirement
        for req_id, data in requirement_compliance.items():
            if data["total_offers"] > 0:
                data["compliance_rate"] = (data["compliance_count"] / data["total_offers"]) * 100
            else:
                data["compliance_rate"] = 0
                
        # Sort by compliance rate (ascending)
        requirement_list = list(requirement_compliance.values())
        requirement_list.sort(key=lambda x: x["compliance_rate"])
        
        # Find problematic requirements (compliance rate < 75%)
        problematic_requirements = [r for r in requirement_list if r["compliance_rate"] < 75]
        
        return {
            "analysis_performed": True,
            "offers_analyzed": len(compliance_data),
            "overall_statistics": {
                "average_compliance_rate": avg_compliance,
                "average_mandatory_compliance_rate": avg_mandatory_compliance,
                "fully_compliant_offers": len([d for d in compliance_data if d["mandatory_compliance_rate"] == 100])
            },
            "offer_compliance": compliance_data,
            "requirement_analysis": requirement_list,
            "problematic_requirements": problematic_requirements
        }
    
    def _generate_timeline_analysis(self, tender):
        """Generate timeline analysis for a tender report"""
        # Key dates
        timeline = {
            "created": tender.created_at,
            "published": tender.published_at,
            "submission_deadline": tender.submission_deadline,
            "opening_date": tender.opening_date,
            "closed_or_awarded": tender.updated_at if tender.status in ['closed', 'awarded'] else None
        }
        
        # Calculate durations
        durations = {}
        
        if tender.published_at and tender.submission_deadline:
            submission_period = (tender.submission_deadline - tender.published_at).days
            durations["submission_period_days"] = submission_period
            
        if tender.published_at and tender.status in ['closed', 'awarded'] and tender.updated_at:
            total_process = (tender.updated_at - tender.published_at).days
            durations["total_process_days"] = total_process
            
        if tender.status == 'published':
            days_until_deadline = (tender.submission_deadline - timezone.now()).days
            durations["days_until_deadline"] = days_until_deadline
            
        # Get evaluation timeline if applicable
        evaluation_timeline = {}
        if tender.status in ['closed', 'awarded']:
            evaluations = Evaluation.objects.filter(offer__tender=tender)
            
            if evaluations.exists():
                first_evaluation = evaluations.order_by('created_at').first()
                last_evaluation = evaluations.order_by('created_at').last()
                
                evaluation_timeline["first_evaluation"] = first_evaluation.created_at
                evaluation_timeline["last_evaluation"] = last_evaluation.created_at
                
                evaluation_period = (last_evaluation.created_at - first_evaluation.created_at).days
                evaluation_timeline["evaluation_period_days"] = evaluation_period
                
        # Timeline assessment
        assessment = {}
        
        # Submission period assessment
        if "submission_period_days" in durations:
            if durations["submission_period_days"] < 14:
                assessment["submission_period"] = "Very short submission period, which might limit competition"
            elif durations["submission_period_days"] < 21:
                assessment["submission_period"] = "Relatively short submission period"
            elif durations["submission_period_days"] > 60:
                assessment["submission_period"] = "Extended submission period, which may indicate complexity"
                
        # Process efficiency assessment
        if "total_process_days" in durations:
            if durations["total_process_days"] < 30:
                assessment["process_efficiency"] = "Highly efficient procurement process"
            elif durations["total_process_days"] > 90:
                assessment["process_efficiency"] = "Lengthy procurement process, which may impact project timelines"
                
        # Evaluation period assessment
        if evaluation_timeline and "evaluation_period_days" in evaluation_timeline:
            if evaluation_timeline["evaluation_period_days"] < 7:
                assessment["evaluation_period"] = "Rapid evaluation process"
            elif evaluation_timeline["evaluation_period_days"] > 30:
                assessment["evaluation_period"] = "Extended evaluation period, which may indicate complexity or resource constraints"
                
        return {
            "key_dates": {k: v.isoformat() if v else None for k, v in timeline.items()},
            "durations": durations,
            "evaluation_timeline": {
                k: v.isoformat() if isinstance(v, datetime.datetime) else v 
                for k, v in evaluation_timeline.items()
            } if evaluation_timeline else {},
            "assessment": assessment
        }
    
    def _detect_anomalies(self, tender, offers, evaluations):
        """Detect anomalies in tender, offers, and evaluations"""
        anomalies = []
        
        # Price anomalies
        valid_prices = [float(o.price) for o in offers if o.price is not None]
        if len(valid_prices) >= 2:
            avg_price = sum(valid_prices) / len(valid_prices)
            std_dev = math.sqrt(sum((p - avg_price) ** 2 for p in valid_prices) / len(valid_prices))
            
            for offer in offers:
                if offer.price is not None:
                    price = float(offer.price)
                    z_score = abs(price - avg_price) / std_dev if std_dev > 0 else 0
                    
                    if z_score > 2:
                        anomalies.append({
                            "type": "price_anomaly",
                            "severity": "high" if z_score > 3 else "medium",
                            "offer_id": offer.id,
                            "vendor_name": offer.vendor.name,
                            "details": f"Price (${price:,.2f}) deviates significantly from average (${avg_price:,.2f})",
                            "z_score": z_score
                        })
        
        # Evaluation anomalies
        if evaluations.exists():
            # Group evaluations by criteria and offer
            grouped_evaluations = {}
            for evaluation in evaluations:
                offer_id = evaluation.offer.id
                criteria_id = evaluation.criteria.id
                
                key = f"{offer_id}_{criteria_id}"
                if key not in grouped_evaluations:
                    grouped_evaluations[key] = []
                    
                grouped_evaluations[key].append({
                    'id': evaluation.id,
                    'evaluator': evaluation.evaluator.username,
                    'score': float(evaluation.score),
                    'max_score': float(evaluation.criteria.max_score)
                })
            
            # Check for inconsistent evaluations
            for key, evals in grouped_evaluations.items():
                if len(evals) < 2:
                    continue  # Need at least 2 evaluations to detect anomalies
                
                scores = [e['score'] for e in evals]
                avg_score = sum(scores) / len(scores)
                
                # Calculate standard deviation
                variance = sum((score - avg_score) ** 2 for score in scores) / len(scores)
                std_dev = math.sqrt(variance)
                
                # Check for outliers (>2 standard deviations from mean)
                for eval_info in evals:
                    z_score = abs(eval_info['score'] - avg_score) / (std_dev if std_dev > 0 else 1)
                    if z_score > 2:
                        offer_id, criteria_id = map(int, key.split('_'))
                        offer = Offer.objects.get(id=offer_id)
                        criteria = EvaluationCriteria.objects.get(id=criteria_id)
                        
                        anomalies.append({
                            "type": "evaluation_anomaly",
                            "severity": "high" if z_score > 3 else "medium",
                            "evaluation_id": eval_info['id'],
                            "offer_id": offer_id,
                            "vendor_name": offer.vendor.name,
                            "criteria_name": criteria.name,
                            "evaluator": eval_info['evaluator'],
                            "details": f"Score ({eval_info['score']}) deviates significantly from average ({avg_score:.2f}) for this criteria",
                            "z_score": z_score
                        })
        
        # Compliance anomalies
        for offer in offers.filter(status__in=['submitted', 'evaluated', 'awarded']):
            compliance = self._offer_compliance_analysis(offer, tender)
            
            if compliance.get("analysis_performed", False):
                missing_mandatory = len(compliance.get("missing_mandatory_docs", []))
                if missing_mandatory > 0 and offer.status in ['evaluated', 'awarded']:
                    anomalies.append({
                        "type": "compliance_anomaly",
                        "severity": "high",
                        "offer_id": offer.id,
                        "vendor_name": offer.vendor.name,
                        "details": f"Offer is missing {missing_mandatory} mandatory documents but has status '{offer.status}'"
                    })
        
        # Timeline anomalies
        if tender.status == 'closed':
            days_since_closing = (timezone.now() - tender.updated_at).days
            if days_since_closing > 30 and not tender.offers.filter(status='awarded').exists():
                anomalies.append({
                    "type": "timeline_anomaly",
                    "severity": "medium",
                    "details": f"Tender has been closed for {days_since_closing} days without award decision"
                })
                
        # Score-price correlation anomalies
        scored_offers = [o for o in offers if o.total_score is not None and o.price is not None]
        if len(scored_offers) >= 3:
            # Check if highest scored offer has significantly higher price
            sorted_by_score = sorted(scored_offers, key=lambda x: float(x.total_score), reverse=True)
            highest_scored = sorted_by_score[0]
            
            # Compare with average price
            prices = [float(o.price) for o in scored_offers]
            avg_price = sum(prices) / len(prices)
            
            if float(highest_scored.price) > avg_price * 1.5:
                anomalies.append({
                    "type": "score_price_anomaly",
                    "severity": "medium",
                    "offer_id": highest_scored.id,
                    "vendor_name": highest_scored.vendor.name,
                    "details": f"Highest scored offer has price {((float(highest_scored.price) / avg_price) - 1) * 100:.1f}% above average"
                })
        
        return sorted(anomalies, key=lambda x: {"high": 0, "medium": 1, "low": 2}[x["severity"]])
    
    def _assess_risks(self, tender, offers):
        """Assess risks in the procurement process"""
        risks = []
        
        # Limited competition risk
        if offers.filter(status__in=['submitted', 'evaluated', 'awarded', 'rejected']).count() < 3:
            risks.append({
                "risk_type": "limited_competition",
                "severity": "high",
                "description": "Limited competition may result in suboptimal value for money",
                "mitigation": "Consider retendering or extending submission deadline to attract more offers"
            })
            
        # Price variation risk
        valid_prices = [float(o.price) for o in offers if o.price is not None]
        if len(valid_prices) >= 2:
            price_range_percentage = ((max(valid_prices) - min(valid_prices)) / min(valid_prices)) * 100 if min(valid_prices) > 0 else 0
            
            if price_range_percentage > 50:
                risks.append({
                    "risk_type": "high_price_variation",
                    "severity": "medium",
                    "description": f"High price variation ({price_range_percentage:.1f}%) indicates possible misinterpretation of requirements",
                    "mitigation": "Review requirements clarity and consider vendor clarification requests"
                })
                
        # Evaluation consistency risk
        evaluations = Evaluation.objects.filter(offer__tender=tender)
        if evaluations.exists():
            consistency_analysis = self._analyze_evaluation_consistency(tender)
            
            if consistency_analysis.get("analysis_performed", False):
                consistency_rating = consistency_analysis.get("overall_consistency", {}).get("consistency_rating")
                
                if consistency_rating in ["Poor", "Very Poor"]:
                    risks.append({
                        "risk_type": "evaluation_inconsistency",
                        "severity": "high",
                        "description": f"Inconsistent evaluations may lead to challenges to the award decision",
                        "mitigation": "Review evaluation criteria with evaluators and consider calibration session"
                    })
                    
        # Compliance risk
        for offer in offers.filter(status__in=['evaluated', 'awarded']):
            compliance = self._offer_compliance_analysis(offer, tender)
            
            if compliance.get("analysis_performed", False):
                mandatory_compliance = compliance.get("mandatory_compliance_rate", 100)
                
                if mandatory_compliance < 100:
                    risks.append({
                        "risk_type": "non_compliance",
                        "severity": "high",
                        "offer_id": offer.id,
                        "vendor_name": offer.vendor.name,
                        "description": f"Offer with status '{offer.status}' is missing mandatory documentation",
                        "mitigation": "Request missing documentation before proceeding with award"
                    })
                    
        # Timeline risk
        if tender.status == 'published' and tender.submission_deadline:
            days_until_deadline = (tender.submission_deadline - timezone.now()).days
            
            if days_until_deadline < 7 and offers.count() < 2:
                risks.append({
                    "risk_type": "deadline_approaching",
                    "severity": "medium",
                    "description": f"Submission deadline is approaching with limited offers received",
                    "mitigation": "Consider extending deadline to attract more competition"
                })
                
        # Award delay risk
        if tender.status == 'closed':
            days_since_closing = (timezone.now() - tender.updated_at).days
            
            if days_since_closing > 30:
                risks.append({
                    "risk_type": "award_delay",
                    "severity": "medium",
                    "description": f"Tender has been closed for {days_since_closing} days without award decision",
                    "mitigation": "Accelerate evaluation process to maintain vendor interest"
                })
                
        # Financial risk for lowest priced offer
        valid_offers = [o for o in offers if o.price is not None]
        if len(valid_offers) >= 3:
            sorted_by_price = sorted(valid_offers, key=lambda x: float(x.price))
            lowest_priced = sorted_by_price[0]
            second_lowest = sorted_by_price[1]
            
            price_difference = (float(second_lowest.price) - float(lowest_priced.price)) / float(lowest_priced.price) * 100
            
            if price_difference > 30:
                risks.append({
                    "risk_type": "unrealistic_pricing",
                    "severity": "medium",
                    "offer_id": lowest_priced.id,
                    "vendor_name": lowest_priced.vendor.name,
                    "description": f"Lowest priced offer is {price_difference:.1f}% below the second lowest offer",
                    "mitigation": "Verify that all requirements are understood and can be met at this price"
                })
        
        return sorted(risks, key=lambda x: {"high": 0, "medium": 1, "low": 2}[x["severity"]])
    
    def _generate_final_recommendations(self, tender, offers):
        """Generate final recommendations for a tender"""
        recommendations = []
        
        # Process improvement recommendations
        if tender.status == 'draft':
            # Recommendations for draft tenders
            requirements = tender.requirements.all()
            
            if not requirements.exists():
                recommendations.append({
                    "category": "process_improvement",
                    "description": "Define clear requirements before publishing the tender",
                    "rationale": "Clear requirements help vendors submit responsive offers"
                })
                
            if not tender.evaluation_criteria.exists():
                recommendations.append({
                    "category": "process_improvement",
                    "description": "Define evaluation criteria before publishing the tender",
                    "rationale": "Transparent evaluation criteria improve fairness and reduce challenges"
                })
                
        elif tender.status == 'published':
            # Recommendations for published tenders
            days_published = (timezone.now() - tender.published_at).days if tender.published_at else 0
            offers_received = offers.count()
            
            if days_published > 14 and offers_received < 2:
                recommendations.append({
                    "category": "process_improvement",
                    "description": "Consider extending submission deadline to attract more offers",
                    "rationale": "Limited competition may result in suboptimal value for money"
                })
                
        elif tender.status == 'closed':
            # Recommendations for closed tenders
            days_closed = (timezone.now() - tender.updated_at).days
            
            if days_closed > 21 and not offers.filter(status='awarded').exists():
                recommendations.append({
                    "category": "process_improvement",
                    "description": "Accelerate the evaluation and award process",
                    "rationale": "Delays may impact project implementation and vendor interest"
                })
                
            # Check evaluation consistency
            eval_consistency = self._analyze_evaluation_consistency(tender)
            if eval_consistency.get("analysis_performed", False):
                consistency_rating = eval_consistency.get("overall_consistency", {}).get("consistency_rating")
                
                if consistency_rating in ["Poor", "Very Poor"]:
                    recommendations.append({
                        "category": "evaluation_improvement",
                        "description": "Review evaluation criteria and scores for consistency",
                        "rationale": "Inconsistent evaluations may lead to challenges and disputes"
                    })
                    
        # Award recommendations
        if tender.status == 'closed' and not offers.filter(status='awarded').exists():
            scored_offers = offers.filter(
                total_score__isnull=False
            ).order_by('-total_score')
            
            if scored_offers.exists():
                top_offer = scored_offers.first()
                
                # Check for compliance issues
                compliance = self._offer_compliance_analysis(top_offer, tender)
                if compliance.get("analysis_performed", False) and compliance.get("mandatory_compliance_rate", 100) < 100:
                    recommendations.append({
                        "category": "award_recommendation",
                        "description": f"Request missing mandatory documents from {top_offer.vendor.name} before award decision",
                        "rationale": "Ensures compliance with tender requirements"
                    })
                else:
                    recommendations.append({
                        "category": "award_recommendation",
                        "description": f"Consider awarding the tender to {top_offer.vendor.name}",
                        "rationale": f"Highest scored offer with total score of {float(top_offer.total_score):.2f}"
                    })
                    
        # Future improvements
        if tender.status == 'awarded':
            recommendations.append({
                "category": "future_improvement",
                "description": "Document lessons learned for future procurement processes",
                "rationale": "Continuous improvement of procurement practices"
            })
            
            # Contract management recommendation
            awarded_offer = offers.filter(status='awarded').first()
            if awarded_offer:
                recommendations.append({
                    "category": "contract_management",
                    "description": f"Establish key performance indicators for monitoring contract with {awarded_offer.vendor.name}",
                    "rationale": "Ensures delivery according to requirements and specifications"
                })
                
        return recommendations
    
    def _generate_evaluation_summary(self, tender, evaluations):
        """Generate evaluation summary for a focused report"""
        if not evaluations.exists():
            return {
                "status": "No evaluations found",
                "evaluations_count": 0
            }
            
        # Basic statistics
        total_evaluations = evaluations.count()
        evaluator_count = evaluations.values('evaluator_id').distinct().count()
        
        # Group evaluations by offer
        offer_evaluations = {}
        for evaluation in evaluations:
            offer_id = evaluation.offer.id
            
            if offer_id not in offer_evaluations:
                offer_evaluations[offer_id] = {
                    "offer_id": offer_id,
                    "vendor_name": evaluation.offer.vendor.name,
                    "total_evaluations": 0,
                    "average_score": 0,
                    "scores": []
                }
                
            offer_evaluations[offer_id]["total_evaluations"] += 1
            offer_evaluations[offer_id]["scores"].append(float(evaluation.score))
            
        # Calculate average scores
        for offer_id, data in offer_evaluations.items():
            data["average_score"] = sum(data["scores"]) / len(data["scores"]) if data["scores"] else 0
            del data["scores"]  # Remove raw scores from output
            
        # Sort by average score
        offer_evaluation_list = list(offer_evaluations.values())
        offer_evaluation_list.sort(key=lambda x: x["average_score"], reverse=True)
        
        # Calculate overall statistics
        avg_scores = [data["average_score"] for data in offer_evaluation_list]
        overall_avg = sum(avg_scores) / len(avg_scores) if avg_scores else 0
        
        # Get final scores for offers
        offers = Offer.objects.filter(tender=tender, total_score__isnull=False)
        final_scores = []
        
        for offer in offers:
            final_scores.append({
                "offer_id": offer.id,
                "vendor_name": offer.vendor.name,
                "technical_score": float(offer.technical_score) if offer.technical_score else None,
                "financial_score": float(offer.financial_score) if offer.financial_score else None,
                "total_score": float(offer.total_score) if offer.total_score else None
            })
            
        final_scores.sort(key=lambda x: x["total_score"] if x["total_score"] is not None else 0, reverse=True)
        
        return {
            "status": "Evaluation summary generated",
            "evaluations_count": total_evaluations,
            "evaluator_count": evaluator_count,
            "average_evaluation_score": overall_avg,
            "offer_evaluations": offer_evaluation_list,
            "final_scores": final_scores
        }
    
    def _analyze_evaluator_consistency(self, evaluations):
        """Analyze consistency among evaluators"""
        if not evaluations.exists():
            return {
                "analysis_performed": False,
                "reason": "No evaluations found"
            }
            
        # Group evaluations by evaluator
        evaluator_data = {}
        for evaluation in evaluations:
            evaluator_id = evaluation.evaluator.id
            
            if evaluator_id not in evaluator_data:
                evaluator_data[evaluator_id] = {
                    "evaluator_id": evaluator_id,
                    "evaluator_name": evaluation.evaluator.username,
                    "evaluation_count": 0,
                    "scores": [],
                    "normalized_scores": []
                }
                
            evaluator_data[evaluator_id]["evaluation_count"] += 1
            
            score = float(evaluation.score)
            max_score = float(evaluation.criteria.max_score)
            normalized_score = (score / max_score) * 100 if max_score > 0 else 0
            
            evaluator_data[evaluator_id]["scores"].append(score)
            evaluator_data[evaluator_id]["normalized_scores"].append(normalized_score)
            
        # Calculate average scores and tendencies
        evaluator_profiles = []
        normalized_averages = []
        
        for evaluator_id, data in evaluator_data.items():
            avg_score = sum(data["scores"]) / len(data["scores"]) if data["scores"] else 0
            avg_normalized = sum(data["normalized_scores"]) / len(data["normalized_scores"]) if data["normalized_scores"] else 0
            normalized_averages.append(avg_normalized)
            
            evaluator_profiles.append({
                "evaluator_id": evaluator_id,
                "evaluator_name": data["evaluator_name"],
                "evaluation_count": data["evaluation_count"],
                "average_score": avg_score,
                "average_normalized_score": avg_normalized
            })
            
        # Calculate grand average
        grand_avg = sum(normalized_averages) / len(normalized_averages) if normalized_averages else 0
        
        # Determine evaluator tendencies
        for profile in evaluator_profiles:
            deviation = profile["average_normalized_score"] - grand_avg
            
            if deviation > 10:
                tendency = "lenient"
            elif deviation < -10:
                tendency = "strict"
            else:
                tendency = "neutral"
                
            profile["tendency"] = tendency
            profile["deviation_from_average"] = deviation
            
        # Calculate consistency measures
        consistency_metrics = {
            "evaluator_count": len(evaluator_profiles),
            "score_range": max(normalized_averages) - min(normalized_averages) if normalized_averages else 0,
            "consistency_rating": self._get_consistency_rating_from_range(max(normalized_averages) - min(normalized_averages) if normalized_averages else 0)
        }
        
        return {
            "analysis_performed": True,
            "evaluator_profiles": sorted(evaluator_profiles, key=lambda x: x["average_normalized_score"], reverse=True),
            "consistency_metrics": consistency_metrics
        }
    
    def _get_consistency_rating_from_range(self, range_value):
        """Get a qualitative rating for consistency based on range"""
        if range_value < 10:
            return "Excellent"
        elif range_value < 20:
            return "Good"
        elif range_value < 30:
            return "Moderate"
        elif range_value < 40:
            return "Poor"
        else:
            return "Very Poor"
    
    def _analyze_evaluation_criteria(self, tender):
        """Analyze evaluation criteria"""
        criteria = EvaluationCriteria.objects.filter(tender=tender)
        
        if not criteria.exists():
            return {
                "analysis_performed": False,
                "reason": "No evaluation criteria found"
            }
            
        # Group criteria by category
        criteria_by_category = {}
        for criterion in criteria:
            category = criterion.category
            
            if category not in criteria_by_category:
                criteria_by_category[category] = []
                
            criteria_by_category[category].append({
                "criteria_id": criterion.id,
                "name": criterion.name,
                "weight": float(criterion.weight),
                "max_score": float(criterion.max_score)
            })
            
        # Calculate category weights
        category_weights = {}
        for category, criteria_list in criteria_by_category.items():
            total_weight = sum(c["weight"] for c in criteria_list)
            category_weights[category] = total_weight
            
        # Sort criteria by weight within each category
        for category, criteria_list in criteria_by_category.items():
            criteria_by_category[category] = sorted(criteria_list, key=lambda x: x["weight"], reverse=True)
            
        # Get average evaluation scores per criteria
        evaluations = Evaluation.objects.filter(offer__tender=tender)
        
        if evaluations.exists():
            criteria_scores = {}
            for evaluation in evaluations:
                criteria_id = evaluation.criteria.id
                
                if criteria_id not in criteria_scores:
                    criteria_scores[criteria_id] = {
                        "scores": [],
                        "normalized_scores": []
                    }
                    
                score = float(evaluation.score)
                max_score = float(evaluation.criteria.max_score)
                normalized_score = (score / max_score) * 100 if max_score > 0 else 0
                
                criteria_scores[criteria_id]["scores"].append(score)
                criteria_scores[criteria_id]["normalized_scores"].append(normalized_score)
                
            # Calculate average scores
            for criteria_id, scores_data in criteria_scores.items():
                avg_score = sum(scores_data["scores"]) / len(scores_data["scores"]) if scores_data["scores"] else 0
                avg_normalized = sum(scores_data["normalized_scores"]) / len(scores_data["normalized_scores"]) if scores_data["normalized_scores"] else 0
                
                # Add to criteria data
                for category, criteria_list in criteria_by_category.items():
                    for criterion in criteria_list:
                        if criterion["criteria_id"] == criteria_id:
                            criterion["average_score"] = avg_score
                            criterion["average_normalized_score"] = avg_normalized
                            criterion["evaluation_count"] = len(scores_data["scores"])
                            
                            # Calculate score variance
                            if len(scores_data["normalized_scores"]) >= 2:
                                variance = sum((s - avg_normalized) ** 2 for s in scores_data["normalized_scores"]) / len(scores_data["normalized_scores"])
                                criterion["score_variance"] = variance
                            else:
                                criterion["score_variance"] = 0
            
        return {
            "analysis_performed": True,
            "categories": list(criteria_by_category.keys()),
            "category_weights": category_weights,
            "criteria_by_category": criteria_by_category,
            "total_criteria": criteria.count()
        }
    
    def _analyze_score_distribution(self, evaluations):
        """Analyze the distribution of evaluation scores"""
        if not evaluations.exists():
            return {
                "analysis_performed": False,
                "reason": "No evaluations found"
            }
            
        # Get normalized scores
        normalized_scores = []
        for evaluation in evaluations:
            score = float(evaluation.score)
            max_score = float(evaluation.criteria.max_score)
            normalized_score = (score / max_score) * 100 if max_score > 0 else 0
            normalized_scores.append(normalized_score)
            
        # Basic statistics
        avg_score = sum(normalized_scores) / len(normalized_scores)
        sorted_scores = sorted(normalized_scores)
        median_score = sorted_scores[len(sorted_scores) // 2]
        
        if len(sorted_scores) >= 2:
            variance = sum((s - avg_score) ** 2 for s in normalized_scores) / len(normalized_scores)
            std_dev = math.sqrt(variance)
        else:
            variance = 0
            std_dev = 0
            
        # Score distribution by range
        distribution = {
            "0-10": len([s for s in normalized_scores if s <= 10]),
            "11-20": len([s for s in normalized_scores if s > 10 and s <= 20]),
            "21-30": len([s for s in normalized_scores if s > 20 and s <= 30]),
            "31-40": len([s for s in normalized_scores if s > 30 and s <= 40]),
            "41-50": len([s for s in normalized_scores if s > 40 and s <= 50]),
            "51-60": len([s for s in normalized_scores if s > 50 and s <= 60]),
            "61-70": len([s for s in normalized_scores if s > 60 and s <= 70]),
            "71-80": len([s for s in normalized_scores if s > 70 and s <= 80]),
            "81-90": len([s for s in normalized_scores if s > 80 and s <= 90]),
            "91-100": len([s for s in normalized_scores if s > 90])
        }
        
        # Calculate distribution by evaluator
        evaluator_distribution = {}
        for evaluation in evaluations:
            evaluator_id = evaluation.evaluator.id
            evaluator_name = evaluation.evaluator.username
            
            if evaluator_id not in evaluator_distribution:
                evaluator_distribution[evaluator_id] = {
                    "evaluator_id": evaluator_id,
                    "evaluator_name": evaluator_name,
                    "scores": []
                }
                
            score = float(evaluation.score)
            max_score = float(evaluation.criteria.max_score)
            normalized_score = (score / max_score) * 100 if max_score > 0 else 0
            evaluator_distribution[evaluator_id]["scores"].append(normalized_score)
            
        # Calculate distribution metrics for each evaluator
        for evaluator_id, data in evaluator_distribution.items():
            scores = data["scores"]
            e_avg = sum(scores) / len(scores) if scores else 0
            
            if len(scores) >= 2:
                e_variance = sum((s - e_avg) ** 2 for s in scores) / len(scores)
                e_std_dev = math.sqrt(e_variance)
            else:
                e_variance = 0
                e_std_dev = 0
                
            data["average_score"] = e_avg
            data["variance"] = e_variance
            data["standard_deviation"] = e_std_dev
            
            # Remove raw scores from output
            del data["scores"]
            
        return {
            "analysis_performed": True,
            "basic_statistics": {
                "count": len(normalized_scores),
                "mean": avg_score,
                "median": median_score,
                "variance": variance,
                "standard_deviation": std_dev
            },
            "distribution": distribution,
            "evaluator_distribution": list(evaluator_distribution.values())
        }
    
    def _generate_evaluation_recommendations(self, tender, evaluations):
        """Generate recommendations based on evaluation analysis"""
        recommendations = []
        
        # Check if evaluations exist
        if not evaluations.exists():
            recommendations.append({
                "category": "evaluation_process",
                "description": "Ensure that evaluators complete their assessments",
                "rationale": "No evaluations have been recorded yet"
            })
            return recommendations
            
        # Analyze evaluation consistency
        consistency = self._analyze_evaluator_consistency(evaluations)
        if consistency.get("analysis_performed", False):
            consistency_metrics = consistency.get("consistency_metrics", {})
            consistency_rating = consistency_metrics.get("consistency_rating")
            
            if consistency_rating in ["Poor", "Very Poor"]:
                recommendations.append({
                    "category": "evaluation_consistency",
                    "description": "Organize a calibration session for evaluators",
                    "rationale": f"Evaluation consistency is rated as '{consistency_rating}'"
                })
                
            # Check for biased evaluators
            biased_evaluators = [
                profile for profile in consistency.get("evaluator_profiles", [])
                if abs(profile.get("deviation_from_average", 0)) > 15
            ]
            
            if biased_evaluators:
                recommendations.append({
                    "category": "evaluator_bias",
                    "description": "Review evaluation scores from evaluators with extreme tendencies",
                    "rationale": f"Found {len(biased_evaluators)} evaluators with potential bias"
                })
                
        # Analyze score distribution
        distribution = self._analyze_score_distribution(evaluations)
        if distribution.get("analysis_performed", False):
            basic_stats = distribution.get("basic_statistics", {})
            std_dev = basic_stats.get("standard_deviation", 0)
            
            if std_dev > 20:
                recommendations.append({
                    "category": "score_distribution",
                    "description": "Review evaluation criteria for clarity and interpretation",
                    "rationale": f"High variation in evaluation scores (std. dev. {std_dev:.2f})"
                })
                
        # Analyze criteria
        criteria_analysis = self._analyze_evaluation_criteria(tender)
        if criteria_analysis.get("analysis_performed", False):
            # Check for criteria with high variance
            high_variance_criteria = []
            
            for category, criteria_list in criteria_analysis.get("criteria_by_category", {}).items():
                for criterion in criteria_list:
                    if criterion.get("score_variance", 0) > 400:  # Arbitrary threshold
                        high_variance_criteria.append(criterion)
                        
            if high_variance_criteria:
                recommendations.append({
                    "category": "criteria_clarity",
                    "description": "Clarify evaluation methodology for specific criteria",
                    "rationale": f"Found {len(high_variance_criteria)} criteria with high scoring variance"
                })
                
            # Check category balance
            category_weights = criteria_analysis.get("category_weights", {})
            if 'technical' in category_weights and 'financial' in category_weights:
                tech_weight = category_weights['technical']
                fin_weight = category_weights['financial']
                
                if tech_weight < 50 or fin_weight < 20:
                    recommendations.append({
                        "category": "criteria_balance",
                        "description": "Review balance between technical and financial criteria",
                        "rationale": f"Current weights: Technical {tech_weight}%, Financial {fin_weight}%"
                    })
                    
        # Process recommendations
        if evaluations.exists() and not tender.offers.filter(status='awarded').exists():
            recommendations.append({
                "category": "evaluation_process",
                "description": "Complete the evaluation process and proceed to award decision",
                "rationale": "Evaluations have been performed but no award decision has been made"
            })
        
        return recommendations
    
    def _generate_financial_summary(self, tender, offers):
        """Generate financial summary for a price-focused report"""
        valid_offers = [o for o in offers if o.price is not None]
        
        if not valid_offers:
            return {
                "status": "No offers with price information found",
                "offers_count": 0
            }
            
        # Extract prices
        prices = [float(o.price) for o in valid_offers]
        
        # Basic statistics
        avg_price = sum(prices) / len(prices)
        median_price = sorted(prices)[len(prices) // 2]
        min_price = min(prices)
        max_price = max(prices)
        price_range = max_price - min_price
        
        # Variance and standard deviation
        variance = sum((p - avg_price) ** 2 for p in prices) / len(prices)
        std_dev = math.sqrt(variance)
        
        # Coefficient of variation
        coef_var = (std_dev / avg_price) * 100 if avg_price > 0 else 0
        
        # Prepare offer summaries
        offer_summaries = []
        for offer in valid_offers:
            offer_price = float(offer.price)
            deviation = ((offer_price - avg_price) / avg_price) * 100
            
            offer_summaries.append({
                "offer_id": offer.id,
                "vendor_name": offer.vendor.name,
                "price": offer_price,
                "deviation_from_average": deviation,
                "price_ranking": sorted(prices).index(offer_price) + 1,
                "status": offer.status
            })
            
        # Sort by price
        offer_summaries.sort(key=lambda x: x["price"])
        
        # Price clustering
        clusters = self._cluster_prices(prices)
        
        # Benchmark assessment
        estimated_value = float(tender.estimated_value) if tender.estimated_value else None
        benchmark_assessment = {}
        
        if estimated_value:
            avg_deviation = ((avg_price - estimated_value) / estimated_value) * 100
            
            benchmark_assessment = {
                "estimated_value": estimated_value,
                "average_deviation": avg_deviation,
                "market_assessment": "Competitive" if abs(avg_deviation) < 10 else
                                    "Somewhat competitive" if abs(avg_deviation) < 20 else
                                    "Not competitive"
            }
        
        return {
            "analysis_performed": True,
            "offers_analyzed": len(valid_offers),
            "basic_statistics": {
                "average_price": avg_price,
                "median_price": median_price,
                "min_price": min_price,
                "max_price": max_price,
                "price_range": price_range,
                "price_range_percentage": (price_range / min_price) * 100 if min_price > 0 else 0
            },
            "price_clusters": clusters,
            "benchmark_assessment": benchmark_assessment if estimated_value else None
        }

    def _analyze_price_details(self, offers):
        """Analyze prices in detail for financial reporting"""
        valid_offers = [o for o in offers if o.price is not None]
        
        if not valid_offers:
            return {
                "analysis_performed": False,
                "reason": "No offers with valid prices"
            }
            
        # Extract prices
        prices = [float(o.price) for o in valid_offers]
        
        # Basic statistics
        avg_price = sum(prices) / len(prices)
        median_price = sorted(prices)[len(prices) // 2]
        min_price = min(prices)
        max_price = max(prices)
        price_range = max_price - min_price
        
        # Variance and standard deviation
        variance = sum((p - avg_price) ** 2 for p in prices) / len(prices)
        std_dev = math.sqrt(variance)
        
        # Prepare offer details
        offer_details = []
        for offer in valid_offers:
            price = float(offer.price)
            deviation = ((price - avg_price) / avg_price) * 100 if avg_price > 0 else 0
            
            offer_details.append({
                "offer_id": offer.id,
                "vendor_name": offer.vendor.name,
                "price": price,
                "deviation_from_avg": deviation,
                "deviation_description": "Average" if abs(deviation) < 10 else
                                         "Above average" if deviation > 0 else
                                         "Below average",
                "price_rank": sorted(prices).index(price) + 1,
                "percentile": sorted(prices).index(price) / len(prices) * 100
            })
            
        # Sort by price
        offer_details.sort(key=lambda x: x["price"])
        
        # Check for outliers
        outliers = []
        if std_dev > 0:
            for offer in offer_details:
                z_score = abs(offer["price"] - avg_price) / std_dev
                if z_score > 2:
                    outliers.append({
                        "offer_id": offer["offer_id"],
                        "vendor_name": offer["vendor_name"],
                        "price": offer["price"],
                        "z_score": z_score,
                        "deviation_percentage": offer["deviation_from_avg"]
                    })
        
        return {
            "analysis_performed": True,
            "basic_statistics": {
                "average_price": avg_price,
                "median_price": median_price,
                "min_price": min_price,
                "max_price": max_price,
                "std_deviation": std_dev,
                "coefficient_of_variation": (std_dev / avg_price) * 100 if avg_price > 0 else 0
            },
            "offer_details": offer_details,
            "outliers": outliers
        }
    
    def _market_price_comparison(self, tender, offers):
        """Compare tender prices with market estimates"""
        valid_offers = [o for o in offers if o.price is not None]
        
        if not valid_offers:
            return {
                "analysis_performed": False,
                "reason": "No offers with valid prices"
            }
            
        # Check if tender has estimated value
        estimated_value = float(tender.estimated_value) if tender.estimated_value else None
        
        if not estimated_value:
            return {
                "analysis_performed": False,
                "reason": "No estimated value available for comparison"
            }
            
        # Extract prices
        prices = [float(o.price) for o in valid_offers]
        avg_price = sum(prices) / len(prices)
        
        # Calculate deviation from estimate
        market_deviation = ((avg_price - estimated_value) / estimated_value) * 100
        
        # Determine if prices are within expected range
        offers_within_range = sum(1 for p in prices if abs((p - estimated_value) / estimated_value) <= 0.15)
        percentage_within_range = (offers_within_range / len(prices)) * 100
        
        # Analyze if the estimated value was accurate
        if abs(market_deviation) < 10:
            estimate_accuracy = "Highly accurate"
        elif abs(market_deviation) < 20:
            estimate_accuracy = "Moderately accurate"
        else:
            estimate_accuracy = "Not accurate"
            
        # Overall market assessment
        if market_deviation < -15:
            market_assessment = "Prices significantly below estimate (competitive market)"
        elif market_deviation < 0:
            market_assessment = "Prices slightly below estimate (healthy competition)"
        elif market_deviation < 15:
            market_assessment = "Prices in line with estimate (expected market)"
        else:
            market_assessment = "Prices significantly above estimate (potential market issues)"
            
        return {
            "analysis_performed": True,
            "estimated_value": estimated_value,
            "average_price": avg_price,
            "market_deviation": market_deviation,
            "offers_within_range": offers_within_range,
            "percentage_within_range": percentage_within_range,
            "estimate_accuracy": estimate_accuracy,
            "market_assessment": market_assessment
        }
    
    def _calculate_value_for_money(self, offers):
        """Calculate value for money metrics for offers"""
        valid_offers = [o for o in offers if o.price is not None and o.technical_score is not None]
        
        if not valid_offers:
            return {
                "analysis_performed": False,
                "reason": "No offers with both price and technical score"
            }
            
        # Calculate value for money for each offer (technical score / price)
        vfm_data = []
        for offer in valid_offers:
            price = float(offer.price)
            technical_score = float(offer.technical_score)
            
            # Avoid division by zero
            if price > 0:
                vfm = technical_score / price * 1000  # Normalized to a more readable scale
            else:
                vfm = 0
                
            vfm_data.append({
                "offer_id": offer.id,
                "vendor_name": offer.vendor.name,
                "price": price,
                "technical_score": technical_score,
                "value_for_money": vfm
            })
            
        # Sort by value for money (descending)
        vfm_data.sort(key=lambda x: x["value_for_money"], reverse=True)
        
        # Calculate average VFM
        avg_vfm = sum(item["value_for_money"] for item in vfm_data) / len(vfm_data)
        
        # Identify best value offers (top 25%)
        best_value_threshold = len(vfm_data) // 4
        best_value_offers = vfm_data[:max(1, best_value_threshold)]
        
        return {
            "analysis_performed": True,
            "offer_vfm_data": vfm_data,
            "average_vfm": avg_vfm,
            "best_value_offers": best_value_offers
        }
    
    def _budgetary_assessment(self, tender, offers):
        """Assess budgetary implications of tender"""
        valid_offers = [o for o in offers if o.price is not None]
        
        if not valid_offers:
            return {
                "analysis_performed": False,
                "reason": "No offers with valid prices"
            }
            
        # Check if tender has estimated value
        estimated_value = float(tender.estimated_value) if tender.estimated_value else None
        
        # Basic statistics
        prices = [float(o.price) for o in valid_offers]
        min_price = min(prices)
        max_price = max(prices)
        avg_price = sum(prices) / len(prices)
        
        # Prepare assessment
        assessment = {
            "price_range": max_price - min_price,
            "average_price": avg_price,
            "total_value": sum(prices)
        }
        
        if estimated_value:
            assessment["estimated_value"] = estimated_value
            assessment["budget_variance"] = avg_price - estimated_value
            assessment["budget_variance_percentage"] = ((avg_price - estimated_value) / estimated_value) * 100
            
            # Budget assessment
            if avg_price <= estimated_value * 0.85:
                assessment["budget_assessment"] = "Significantly under budget"
            elif avg_price <= estimated_value:
                assessment["budget_assessment"] = "Within budget"
            elif avg_price <= estimated_value * 1.15:
                assessment["budget_assessment"] = "Slightly over budget"
            else:
                assessment["budget_assessment"] = "Significantly over budget"
        
        return {
            "analysis_performed": True,
            "assessment": assessment
        }
    
    def _generate_financial_recommendations(self, tender, offers):
        """Generate financial recommendations based on analysis"""
        valid_offers = [o for o in offers if o.price is not None]
        
        if not valid_offers:
            return []
            
        recommendations = []
        
        # Extract prices
        prices = [float(o.price) for o in valid_offers]
        avg_price = sum(prices) / len(prices)
        min_price = min(prices)
        max_price = max(prices)
        price_range_percentage = ((max_price - min_price) / min_price) * 100 if min_price > 0 else 0
        
        # Check if tender has estimated value
        estimated_value = float(tender.estimated_value) if tender.estimated_value else None
        
        # Recommendation 1: High price variation
        if price_range_percentage > 40:
            recommendations.append({
                "type": "warning",
                "issue": "High price variation",
                "description": f"Price spread is {price_range_percentage:.1f}%, indicating significant variation in offers.",
                "suggested_action": "Verify that all vendors understood requirements correctly and are offering comparable solutions."
            })
            
        # Recommendation 2: Prices significantly above estimate
        if estimated_value and avg_price > estimated_value * 1.2:
            recommendations.append({
                "type": "warning",
                "issue": "Prices above estimate",
                "description": f"Average price is {((avg_price - estimated_value) / estimated_value) * 100:.1f}% above estimated value.",
                "suggested_action": "Review requirements to ensure they are not overly restrictive, or consider adjusting the budget."
            })
            
        # Recommendation 3: Lowest price outlier
        if len(prices) >= 3:
            second_lowest = sorted(prices)[1]
            if min_price < second_lowest * 0.7:
                recommendations.append({
                    "type": "warning",
                    "issue": "Unusually low price",
                    "description": "The lowest price is significantly below other offers.",
                    "suggested_action": "Verify that the lowest offer meets all requirements and can be delivered at the quoted price."
                })
                
        # Recommendation 4: Consider value for money
        if any(o.technical_score is not None for o in valid_offers):
            recommendations.append({
                "type": "info",
                "issue": "Consider value for money",
                "description": "Some offers may provide better value despite higher prices.",
                "suggested_action": "Evaluate technical scores alongside prices for a holistic assessment."
            })
            
        return recommendations
    
    def _analyze_vendor_time_performance(self, vendor, offers):
        """Analyze vendor performance over time"""
        if not offers.exists():
            return {
                "analysis_performed": False,
                "reason": "No offers available for analysis"
            }
            
        # Group offers by year and month
        time_series = {}
        for offer in offers.order_by('created_at'):
            year_month = offer.created_at.strftime('%Y-%m')
            
            if year_month not in time_series:
                time_series[year_month] = {
                    'total': 0,
                    'awarded': 0,
                    'submitted': 0,
                    'rejected': 0,
                    'scores': []
                }
                
            time_series[year_month]['total'] += 1
            
            if offer.status == 'awarded':
                time_series[year_month]['awarded'] += 1
            elif offer.status == 'submitted' or offer.status == 'evaluated':
                time_series[year_month]['submitted'] += 1
            elif offer.status == 'rejected':
                time_series[year_month]['rejected'] += 1
                
            if offer.total_score is not None:
                time_series[year_month]['scores'].append(float(offer.total_score))
                
        # Calculate metrics for each period
        performance_trend = []
        for year_month, data in sorted(time_series.items()):
            avg_score = sum(data['scores']) / len(data['scores']) if data['scores'] else None
            success_rate = data['awarded'] / (data['awarded'] + data['rejected']) * 100 if (data['awarded'] + data['rejected']) > 0 else None
            
            performance_trend.append({
                'period': year_month,
                'total_offers': data['total'],
                'awarded': data['awarded'],
                'submitted': data['submitted'],
                'rejected': data['rejected'],
                'avg_score': avg_score,
                'success_rate': success_rate
            })
            
        # Calculate trend indicators
        if len(performance_trend) >= 2:
            # Analyze last two periods
            current = performance_trend[-1]
            previous = performance_trend[-2]
            
            trend_indicators = {
                'success_rate_trend': 'increasing' if (current.get('success_rate') or 0) > (previous.get('success_rate') or 0) else 
                                      'decreasing' if (current.get('success_rate') or 0) < (previous.get('success_rate') or 0) else
                                      'stable',
                'avg_score_trend': 'increasing' if (current.get('avg_score') or 0) > (previous.get('avg_score') or 0) else
                                   'decreasing' if (current.get('avg_score') or 0) < (previous.get('avg_score') or 0) else
                                   'stable',
                'activity_trend': 'increasing' if current['total_offers'] > previous['total_offers'] else
                                 'decreasing' if current['total_offers'] < previous['total_offers'] else
                                 'stable'
            }
        else:
            trend_indicators = {
                'success_rate_trend': 'not enough data',
                'avg_score_trend': 'not enough data',
                'activity_trend': 'not enough data'
            }
            
        return {
            'analysis_performed': True,
            'performance_trend': performance_trend,
            'trend_indicators': trend_indicators
        }
    
    def _analyze_vendor_competitiveness(self, vendor, offers):
        """Analyze how competitive a vendor is compared to others"""
        if not offers.exists():
            return {
                "analysis_performed": False,
                "reason": "No offers available for analysis"
            }
            
        # Get tenders where this vendor has participated
        tenders_ids = offers.values_list('tender_id', flat=True).distinct()
        
        # For each tender, compare this vendor's offer with others
        competitive_analysis = []
        
        for tender_id in tenders_ids:
            try:
                # Get this vendor's offer for this tender
                vendor_offer = offers.filter(tender_id=tender_id).first()
                
                if not vendor_offer:
                    continue
                    
                # Get all other offers for this tender
                other_offers = Offer.objects.filter(tender_id=tender_id).exclude(vendor=vendor)
                
                if not other_offers.exists():
                    continue
                    
                # Compare prices if available
                price_comparison = None
                if vendor_offer.price is not None:
                    other_prices = [float(o.price) for o in other_offers if o.price is not None]
                    
                    if other_prices:
                        avg_other_price = sum(other_prices) / len(other_prices)
                        price_diff = float(vendor_offer.price) - avg_other_price
                        price_diff_percent = (price_diff / avg_other_price) * 100
                        
                        price_comparison = {
                            'vendor_price': float(vendor_offer.price),
                            'avg_other_price': avg_other_price,
                            'price_difference': price_diff,
                            'price_difference_percent': price_diff_percent,
                            'price_competitiveness': 'Very competitive' if price_diff_percent <= -10 else
                                                     'Competitive' if price_diff_percent <= 0 else
                                                     'Less competitive' if price_diff_percent <= 10 else
                                                     'Not competitive'
                        }
                        
                # Compare scores if available
                score_comparison = None
                if vendor_offer.total_score is not None:
                    other_scores = [float(o.total_score) for o in other_offers if o.total_score is not None]
                    
                    if other_scores:
                        avg_other_score = sum(other_scores) / len(other_scores)
                        score_diff = float(vendor_offer.total_score) - avg_other_score
                        
                        score_comparison = {
                            'vendor_score': float(vendor_offer.total_score),
                            'avg_other_score': avg_other_score,
                            'score_difference': score_diff,
                            'score_competitiveness': 'Excellent' if score_diff >= 10 else
                                                    'Good' if score_diff >= 0 else
                                                    'Below average' if score_diff >= -10 else
                                                    'Poor'
                        }
                        
                # Add to competitive analysis
                if price_comparison or score_comparison:
                    tender = Tender.objects.get(id=tender_id)
                    
                    competitive_analysis.append({
                        'tender_id': tender_id,
                        'tender_reference': tender.reference_number,
                        'tender_title': tender.title,
                        'tender_status': tender.status,
                        'offer_status': vendor_offer.status,
                        'price_comparison': price_comparison,
                        'score_comparison': score_comparison,
                        'submitted_at': vendor_offer.submitted_at
                    })
                    
            except Exception as e:
                logger.error(f"Error in competitive analysis for tender {tender_id}: {str(e)}")
                continue
                
        # Sort by submission date (most recent first)
        competitive_analysis.sort(key=lambda x: x.get('submitted_at') or timezone.now(), reverse=True)
        
        # Calculate overall competitiveness
        if competitive_analysis:
            price_ratings = [c['price_comparison']['price_competitiveness'] for c in competitive_analysis 
                           if c.get('price_comparison')]
                           
            score_ratings = [c['score_comparison']['score_competitiveness'] for c in competitive_analysis 
                           if c.get('score_comparison')]
                           
            # Count ratings
            price_counts = {}
            for rating in price_ratings:
                price_counts[rating] = price_counts.get(rating, 0) + 1
                
            score_counts = {}
            for rating in score_ratings:
                score_counts[rating] = score_counts.get(rating, 0) + 1
                
            # Determine predominant ratings
            price_competitiveness = max(price_counts.items(), key=lambda x: x[1])[0] if price_counts else None
            score_competitiveness = max(score_counts.items(), key=lambda x: x[1])[0] if score_counts else None
            
            overall_assessment = {
                'price_competitiveness': price_competitiveness,
                'score_competitiveness': score_competitiveness,
                'overall_rating': self._get_overall_competitiveness(price_competitiveness, score_competitiveness)
            }
        else:
            overall_assessment = None
            
        return {
            'analysis_performed': True,
            'competitive_analysis': competitive_analysis,
            'tenders_analyzed': len(competitive_analysis),
            'overall_assessment': overall_assessment
        }
    
    def _get_overall_competitiveness(self, price_rating, score_rating):
        """Determine overall competitiveness from price and score ratings"""
        if not price_rating or not score_rating:
            return price_rating or score_rating or "Insufficient data"
            
        # Rating scores (higher is better)
        price_scores = {
            'Very competitive': 4,
            'Competitive': 3,
            'Less competitive': 2,
            'Not competitive': 1
        }
        
        score_scores = {
            'Excellent': 4,
            'Good': 3,
            'Below average': 2,
            'Poor': 1
        }
        
        # Calculate average rating (weight price and score equally)
        price_score = price_scores.get(price_rating, 2)
        quality_score = score_scores.get(score_rating, 2)
        
        avg_score = (price_score + quality_score) / 2
        
        # Map to overall rating
        if avg_score >= 3.5:
            return "Highly competitive"
        elif avg_score >= 2.5:
            return "Competitive"
        elif avg_score >= 1.5:
            return "Moderately competitive"
        else:
            return "Not competitive"
    
    def _analyze_vendor_compliance(self, vendor, offers):
        """Analyze vendor compliance with tender requirements"""
        if not offers.exists():
            return {
                "analysis_performed": False,
                "reason": "No offers available for analysis"
            }
            
        # Count offers with complete documentation
        offers_with_documents = 0
        total_required_docs = 0
        total_submitted_docs = 0
        
        for offer in offers:
            # Count required documents for this tender
            tender_requirements = offer.tender.requirements.filter(is_mandatory=True).count()
            total_required_docs += tender_requirements
            
            # Count submitted documents for this offer
            submitted_documents = offer.documents.count()
            total_submitted_docs += submitted_documents
            
            # Check if all required documents are submitted
            if tender_requirements > 0 and submitted_documents >= tender_requirements:
                offers_with_documents += 1
                
        # Calculate compliance rates
        submission_compliance_rate = (offers_with_documents / offers.count() * 100) if offers.count() > 0 else 0
        document_compliance_rate = (total_submitted_docs / total_required_docs * 100) if total_required_docs > 0 else 100
        
        # Get compliance issues
        compliance_issues = []
        for offer in offers:
            # Find missing documents
            if offer.status not in ['submitted', 'evaluated', 'awarded']:
                continue
                
            required_docs = offer.tender.requirements.filter(is_mandatory=True)
            missing_docs = []
            
            for req in required_docs:
                if not offer.documents.filter(document_type=req.document_type).exists():
                    missing_docs.append(req.document_type)
                    
            if missing_docs:
                compliance_issues.append({
                    'tender_reference': offer.tender.reference_number,
                    'offer_id': offer.id,
                    'missing_documents': missing_docs,
                    'offer_status': offer.status
                })
                
        # Determine compliance rating
        if document_compliance_rate >= 95:
            compliance_rating = "Excellent"
        elif document_compliance_rate >= 85:
            compliance_rating = "Good"
        elif document_compliance_rate >= 70:
            compliance_rating = "Average"
        else:
            compliance_rating = "Poor"
            
        return {
            'analysis_performed': True,
            'offers_analyzed': offers.count(),
            'offers_with_complete_documents': offers_with_documents,
            'submission_compliance_rate': submission_compliance_rate,
            'total_required_docs': total_required_docs,
            'total_submitted_docs': total_submitted_docs,
            'document_compliance_rate': document_compliance_rate,
            'compliance_rating': compliance_rating,
            'compliance_issues': compliance_issues
        }
    
    def _identify_vendor_strengths_weaknesses(self, vendor, offers):
        """Identify vendor strengths and weaknesses based on evaluation data"""
        if not offers.exists():
            return {
                "analysis_performed": False,
                "reason": "No offers available for analysis"
            }
            
        # Get all evaluations for this vendor's offers
        evaluations = Evaluation.objects.filter(offer__vendor=vendor)
        
        if not evaluations.exists():
            return {
                "analysis_performed": False,
                "reason": "No evaluation data available"
            }
            
        # Group evaluations by criteria category
        category_scores = {}
        for evaluation in evaluations:
            category = evaluation.criteria.category
            
            if category not in category_scores:
                category_scores[category] = {
                    'scores': [],
                    'criteria_scores': {}
                }
                
            # Add normalized score (as percentage of max score)
            normalized_score = (float(evaluation.score) / float(evaluation.criteria.max_score)) * 100
            category_scores[category]['scores'].append(normalized_score)
            
            # Track scores by criteria
            criteria_name = evaluation.criteria.name
            if criteria_name not in category_scores[category]['criteria_scores']:
                category_scores[category]['criteria_scores'][criteria_name] = []
                
            category_scores[category]['criteria_scores'][criteria_name].append(normalized_score)
        
        # Calculate average scores by category
        category_averages = {}
        for category, data in category_scores.items():
            category_averages[category] = sum(data['scores']) / len(data['scores'])
            
        # Calculate average scores by criteria
        criteria_averages = {}
        for category, data in category_scores.items():
            for criteria_name, scores in data['criteria_scores'].items():
                criteria_averages[criteria_name] = sum(scores) / len(scores)
                
        # Identify strengths (top 3 criteria)
        strengths = []
        for criteria_name, avg_score in sorted(criteria_averages.items(), key=lambda x: x[1], reverse=True)[:3]:
            strengths.append({
                'criteria': criteria_name,
                'avg_score': avg_score,
                'rating': 'Excellent' if avg_score >= 90 else
                         'Good' if avg_score >= 80 else
                         'Satisfactory'
            })
            
        # Identify weaknesses (bottom 3 criteria)
        weaknesses = []
        for criteria_name, avg_score in sorted(criteria_averages.items(), key=lambda x: x[1])[:3]:
            weaknesses.append({
                'criteria': criteria_name,
                'avg_score': avg_score,
                'rating': 'Poor' if avg_score < 60 else
                         'Needs improvement' if avg_score < 70 else
                         'Average'
            })
            
        # Identify key performance categories
        performance_categories = []
        for category, avg_score in sorted(category_averages.items(), key=lambda x: x[1], reverse=True):
            performance_categories.append({
                'category': category,
                'avg_score': avg_score,
                'rating': 'Excellent' if avg_score >= 90 else
                         'Good' if avg_score >= 80 else
                         'Satisfactory' if avg_score >= 70 else
                         'Needs improvement' if avg_score >= 60 else
                         'Poor'
            })
            
        return {
            'analysis_performed': True,
            'strengths': strengths,
            'weaknesses': weaknesses,
            'performance_by_category': performance_categories
        }
    
    def _generate_vendor_recommendations(self, vendor, offers):
        """Generate recommendations for vendor improvement"""
        recommendations = []
        
        # Check offer success rate
        total_submitted = offers.filter(status__in=['submitted', 'evaluated', 'awarded', 'rejected']).count()
        awarded = offers.filter(status='awarded').count()
        
        if total_submitted > 0:
            success_rate = (awarded / total_submitted) * 100
            
            if success_rate < 20 and total_submitted >= 5:
                recommendations.append({
                    'type': 'improvement',
                    'issue': 'Low success rate',
                    'description': f'Success rate of {success_rate:.1f}% is below average.',
                    'suggested_action': 'Review past unsuccessful offers to identify common weaknesses.'
                })
                
        # Check technical scores
        avg_technical = offers.filter(technical_score__isnull=False).aggregate(
            avg=Avg('technical_score')
        )['avg']
        
        if avg_technical and avg_technical < 70:
            recommendations.append({
                'type': 'improvement',
                'issue': 'Low technical scores',
                'description': f'Average technical score of {avg_technical:.1f} is below the competitive threshold.',
                'suggested_action': 'Focus on improving technical aspects of offers, particularly in documentation quality and compliance with specifications.'
            })
            
        # Check pricing competitiveness
        # Compare prices with other vendors
        price_issues = 0
        for offer in offers:
            if offer.price is None:
                continue
                
            other_offers = Offer.objects.filter(
                tender=offer.tender, 
                price__isnull=False
            ).exclude(vendor=vendor)
            
            if not other_offers.exists():
                continue
                
            other_prices = [float(o.price) for o in other_offers]
            avg_price = sum(other_prices) / len(other_prices)
            
            if float(offer.price) > avg_price * 1.2:  # 20% above average
                price_issues += 1
                
        if price_issues > 0 and price_issues >= total_submitted * 0.3:  # If at least 30% of offers have price issues
            recommendations.append({
                'type': 'improvement',
                'issue': 'Pricing not competitive',
                'description': f'In {price_issues} offers, pricing was significantly above market average.',
                'suggested_action': 'Review pricing strategy to be more competitive while maintaining quality.'
            })
            
        # Check document compliance
        compliance_issues = 0
        for offer in offers:
            required_docs = offer.tender.requirements.filter(is_mandatory=True).count()
            submitted_docs = offer.documents.count()
            
            if required_docs > 0 and submitted_docs < required_docs:
                compliance_issues += 1
                
        if compliance_issues > 0:
            recommendations.append({
                'type': 'improvement',
                'issue': 'Documentation compliance',
                'description': f'{compliance_issues} offers had incomplete documentation.',
                'suggested_action': 'Ensure all required documents are included with each offer submission.'
            })
            
        # Check for consistency
        if total_submitted >= 3:
            # Check consistency in technical scores
            technical_scores = [float(o.technical_score) for o in offers if o.technical_score is not None]
            
            if technical_scores:
                avg_score = sum(technical_scores) / len(technical_scores)
                score_variance = sum((s - avg_score) ** 2 for s in technical_scores) / len(technical_scores)
                
                if score_variance > 100:  # Arbitrary threshold
                    recommendations.append({
                        'type': 'improvement',
                        'issue': 'Inconsistent performance',
                        'description': 'Technical scores vary significantly between offers.',
                        'suggested_action': 'Standardize internal processes to ensure consistent quality across all submissions.'
                    })
                    
        # General recommendation if few others
        if len(recommendations) < 2:
            recommendations.append({
                'type': 'general',
                'issue': 'Continuous improvement',
                'description': 'Even with good performance, there is always room for improvement.',
                'suggested_action': 'Monitor market trends and continuously update capabilities to maintain competitive advantage.'
            })
            
        return recommendations
    
    def _detect_evaluator_bias(self, evaluations):
        """Detect potential evaluator bias in tender evaluations"""
        if not evaluations.exists():
            return []
            
        # Group evaluations by evaluator
        evaluator_scores = {}
        for evaluation in evaluations:
            evaluator_id = evaluation.evaluator.id
            
            if evaluator_id not in evaluator_scores:
                evaluator_scores[evaluator_id] = {
                    'evaluator_id': evaluator_id,
                    'evaluator_name': evaluation.evaluator.username,
                    'scores': [],
                    'normalized_scores': []
                }
                
            # Add raw and normalized scores
            score = float(evaluation.score)
            max_score = float(evaluation.criteria.max_score)
            normalized_score = (score / max_score) * 100 if max_score > 0 else 0
            
            evaluator_scores[evaluator_id]['scores'].append(score)
            evaluator_scores[evaluator_id]['normalized_scores'].append(normalized_score)
            
        # Calculate average normalized score for each evaluator
        evaluator_data = []
        for evaluator_id, data in evaluator_scores.items():
            avg_score = sum(data['scores']) / len(data['scores']) if data['scores'] else 0
            avg_normalized = sum(data['normalized_scores']) / len(data['normalized_scores']) if data['normalized_scores'] else 0
            
            evaluator_data.append({
                'evaluator_id': evaluator_id,
                'evaluator_name': data['evaluator_name'],
                'avg_score': avg_score,
                'avg_normalized_score': avg_normalized,
                'evaluation_count': len(data['scores'])
            })
            
        # Calculate grand average
        all_normalized_scores = [score for data in evaluator_scores.values() for score in data['normalized_scores']]
        grand_avg = sum(all_normalized_scores) / len(all_normalized_scores) if all_normalized_scores else 0
        
        # Identify outlier evaluators (significant deviation from grand average)
        biased_evaluators = []
        for evaluator in evaluator_data:
            deviation = evaluator['avg_normalized_score'] - grand_avg
            
            if abs(deviation) > 15 and evaluator['evaluation_count'] >= 3:  # Significant deviation with enough samples
                biased_evaluators.append({
                    'evaluator_id': evaluator['evaluator_id'],
                    'evaluator_name': evaluator['evaluator_name'],
                    'bias_type': 'lenient' if deviation > 0 else 'strict',
                    'avg_normalized_score': evaluator['avg_normalized_score'],
                    'grand_average': grand_avg,
                    'deviation': deviation,
                    'evaluation_count': evaluator['evaluation_count']
                })
                
        return sorted(biased_evaluators, key=lambda x: abs(x['deviation']), reverse=True)