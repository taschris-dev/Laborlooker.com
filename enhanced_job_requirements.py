"""
Enhanced Job Requirements System for LaborLooker
Implements mandatory 3+ pictures, 10+ word descriptions, and comprehensive validation
"""

import os
import re
from datetime import datetime
from PIL import Image
from werkzeug.utils import secure_filename
from flask import current_app

class JobRequirementsValidator:
    """Validates enhanced job posting requirements"""
    
    def __init__(self):
        self.min_images = 3
        self.min_description_words = 10
        self.max_image_size = 10 * 1024 * 1024  # 10MB
        self.allowed_extensions = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
        self.min_image_dimensions = (400, 300)  # minimum width x height
        self.max_image_dimensions = (4000, 4000)  # maximum width x height
        
    def validate_job_posting(self, title, description, images, budget=None, timeline=None):
        """
        Comprehensive validation of job posting requirements
        
        Args:
            title (str): Job title
            description (str): Job description
            images (list): List of uploaded image files
            budget (float, optional): Job budget
            timeline (str, optional): Expected timeline
            
        Returns:
            tuple: (is_valid, errors, warnings)
        """
        errors = []
        warnings = []
        
        # Validate title
        title_validation = self._validate_title(title)
        if title_validation['errors']:
            errors.extend(title_validation['errors'])
        if title_validation['warnings']:
            warnings.extend(title_validation['warnings'])
            
        # Validate description
        desc_validation = self._validate_description(description)
        if desc_validation['errors']:
            errors.extend(desc_validation['errors'])
        if desc_validation['warnings']:
            warnings.extend(desc_validation['warnings'])
            
        # Validate images
        image_validation = self._validate_images(images)
        if image_validation['errors']:
            errors.extend(image_validation['errors'])
        if image_validation['warnings']:
            warnings.extend(image_validation['warnings'])
            
        # Validate budget if provided
        if budget is not None:
            budget_validation = self._validate_budget(budget)
            if budget_validation['errors']:
                errors.extend(budget_validation['errors'])
            if budget_validation['warnings']:
                warnings.extend(budget_validation['warnings'])
                
        # Validate timeline if provided
        if timeline:
            timeline_validation = self._validate_timeline(timeline)
            if timeline_validation['errors']:
                errors.extend(timeline_validation['errors'])
            if timeline_validation['warnings']:
                warnings.extend(timeline_validation['warnings'])
        
        is_valid = len(errors) == 0
        return is_valid, errors, warnings
    
    def _validate_title(self, title):
        """Validate job title"""
        errors = []
        warnings = []
        
        if not title or not title.strip():
            errors.append("Job title is required")
            return {'errors': errors, 'warnings': warnings}
            
        title = title.strip()
        
        # Length validation
        if len(title) < 5:
            errors.append("Job title must be at least 5 characters long")
        elif len(title) < 10:
            warnings.append("Consider using a more descriptive title (10+ characters recommended)")
            
        if len(title) > 100:
            errors.append("Job title must be 100 characters or less")
            
        # Content validation
        if title.isupper():
            warnings.append("Avoid using ALL CAPS in the title")
            
        # Check for meaningful content
        word_count = len(title.split())
        if word_count < 2:
            warnings.append("Consider using multiple words to better describe the job")
            
        # Check for prohibited patterns
        prohibited_patterns = [
            r'\b(URGENT|ASAP|IMMEDIATE)\b',  # Urgency spam
            r'(\$\$\$|\*\*\*|!!!)',  # Excessive symbols
            r'\b(CLICK HERE|CALL NOW)\b'  # Spam phrases
        ]
        
        for pattern in prohibited_patterns:
            if re.search(pattern, title, re.IGNORECASE):
                warnings.append("Title contains potentially spammy language")
                break
                
        return {'errors': errors, 'warnings': warnings}
    
    def _validate_description(self, description):
        """Validate job description with enhanced requirements"""
        errors = []
        warnings = []
        
        if not description or not description.strip():
            errors.append("Job description is required")
            return {'errors': errors, 'warnings': warnings}
            
        description = description.strip()
        
        # Word count validation (enhanced requirement)
        words = re.findall(r'\b\w+\b', description.lower())
        word_count = len(words)
        
        if word_count < self.min_description_words:
            errors.append(f"Job description must contain at least {self.min_description_words} words (currently {word_count} words)")
        elif word_count < 20:
            warnings.append(f"Consider providing more details ({word_count} words). 20+ words recommended for better responses")
            
        # Length validation
        if len(description) < 50:
            errors.append("Job description must be at least 50 characters long")
        elif len(description) > 5000:
            errors.append("Job description must be 5000 characters or less")
            
        # Content quality validation
        sentences = re.split(r'[.!?]+', description)
        meaningful_sentences = [s.strip() for s in sentences if len(s.strip()) > 5]
        
        if len(meaningful_sentences) < 2:
            warnings.append("Consider breaking your description into multiple sentences for clarity")
            
        # Check for essential information
        essential_keywords = {
            'location': r'\b(location|address|where|site|area|city|town|street|avenue|road|drive|boulevard|lane)\b',
            'timeline': r'\b(when|deadline|timeline|schedule|date|time|soon|urgent|asap|week|month|day)\b',
            'materials': r'\b(materials|supplies|tools|equipment|provide|bring|need|require)\b',
            'skills': r'\b(experience|skill|qualified|certified|license|training|knowledge|ability)\b'
        }
        
        missing_info = []
        for category, pattern in essential_keywords.items():
            if not re.search(pattern, description, re.IGNORECASE):
                missing_info.append(category)
                
        if len(missing_info) > 2:
            warnings.append(f"Consider including information about: {', '.join(missing_info[:3])}")
            
        # Check for contact information (should not be in description)
        contact_patterns = [
            r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b',  # Phone numbers
            r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',  # Email
            r'\b(call|text|email|contact)\s+me\b'  # Direct contact instructions
        ]
        
        for pattern in contact_patterns:
            if re.search(pattern, description, re.IGNORECASE):
                warnings.append("Avoid including personal contact information in the description. Use the platform's messaging system.")
                break
                
        return {'errors': errors, 'warnings': warnings}
    
    def _validate_images(self, images):
        """Validate uploaded images with enhanced requirements"""
        errors = []
        warnings = []
        
        if not images or len(images) == 0:
            errors.append(f"At least {self.min_images} images are required")
            return {'errors': errors, 'warnings': warnings}
            
        # Filter out empty file objects
        valid_images = [img for img in images if img and hasattr(img, 'filename') and img.filename]
        
        if len(valid_images) < self.min_images:
            errors.append(f"At least {self.min_images} images are required (currently {len(valid_images)} provided)")
            
        if len(valid_images) > 15:
            warnings.append("More than 15 images may slow down loading. Consider using only the most relevant photos.")
            
        # Validate each image
        for i, image in enumerate(valid_images):
            image_errors = self._validate_single_image(image, i + 1)
            errors.extend(image_errors)
            
        # Check for variety in images
        if len(valid_images) >= self.min_images:
            image_advice = self._analyze_image_variety(valid_images)
            if image_advice:
                warnings.extend(image_advice)
                
        return {'errors': errors, 'warnings': warnings}
    
    def _validate_single_image(self, image, image_number):
        """Validate a single image file"""
        errors = []
        
        # Check filename
        if not image.filename:
            errors.append(f"Image {image_number}: No filename provided")
            return errors
            
        # Check file extension
        filename = secure_filename(image.filename)
        file_ext = filename.rsplit('.', 1)[1].lower() if '.' in filename else ''
        
        if file_ext not in self.allowed_extensions:
            errors.append(f"Image {image_number}: Invalid file type. Allowed types: {', '.join(self.allowed_extensions)}")
            return errors
            
        # Check file size
        if hasattr(image, 'content_length') and image.content_length:
            if image.content_length > self.max_image_size:
                errors.append(f"Image {image_number}: File too large. Maximum size: {self.max_image_size // (1024*1024)}MB")
                
        # Try to validate image dimensions and format
        try:
            # Reset file pointer to beginning
            image.seek(0)
            
            # Open image with Pillow
            with Image.open(image) as img:
                width, height = img.size
                
                # Check dimensions
                if width < self.min_image_dimensions[0] or height < self.min_image_dimensions[1]:
                    errors.append(f"Image {image_number}: Too small. Minimum size: {self.min_image_dimensions[0]}x{self.min_image_dimensions[1]} pixels")
                    
                if width > self.max_image_dimensions[0] or height > self.max_image_dimensions[1]:
                    errors.append(f"Image {image_number}: Too large. Maximum size: {self.max_image_dimensions[0]}x{self.max_image_dimensions[1]} pixels")
                    
                # Check image format
                if img.format not in ['JPEG', 'PNG', 'GIF', 'WEBP']:
                    errors.append(f"Image {image_number}: Unsupported image format")
                    
            # Reset file pointer for later use
            image.seek(0)
            
        except Exception as e:
            errors.append(f"Image {image_number}: Invalid or corrupted image file")
            
        return errors
    
    def _analyze_image_variety(self, images):
        """Analyze images for variety and provide recommendations"""
        warnings = []
        
        # This is a simplified analysis - in a real implementation,
        # you might use image analysis libraries to detect content
        
        if len(images) >= 3:
            warnings.append("Great! You have multiple images. Consider including: before/during/after shots, different angles, close-ups of specific areas, and overall context photos.")
            
        return warnings
    
    def _validate_budget(self, budget):
        """Validate budget information"""
        errors = []
        warnings = []
        
        try:
            budget_value = float(budget)
            
            if budget_value <= 0:
                errors.append("Budget must be greater than $0")
            elif budget_value < 50:
                warnings.append("Very low budget may result in fewer contractor responses")
            elif budget_value > 100000:
                warnings.append("High budget jobs may require additional verification")
                
        except (ValueError, TypeError):
            errors.append("Budget must be a valid number")
            
        return {'errors': errors, 'warnings': warnings}
    
    def _validate_timeline(self, timeline):
        """Validate timeline information"""
        errors = []
        warnings = []
        
        if not timeline or not timeline.strip():
            return {'errors': errors, 'warnings': warnings}
            
        timeline = timeline.strip().lower()
        
        # Check for reasonable timeline descriptions
        urgent_keywords = ['asap', 'immediate', 'urgent', 'emergency', 'today', 'now']
        if any(keyword in timeline for keyword in urgent_keywords):
            warnings.append("Rush jobs may result in higher costs and fewer contractor options")
            
        # Check for vague timelines
        vague_keywords = ['whenever', 'someday', 'eventually', 'no rush', 'flexible']
        if any(keyword in timeline for keyword in vague_keywords):
            warnings.append("Providing a more specific timeline helps contractors plan better")
            
        return {'errors': errors, 'warnings': warnings}
    
    def generate_improvement_suggestions(self, title, description, image_count):
        """Generate specific suggestions for improving job posts"""
        suggestions = []
        
        # Title suggestions
        if title and len(title.split()) < 3:
            suggestions.append("💡 Title: Add more descriptive words (e.g., 'Kitchen Renovation' → 'Complete Kitchen Renovation in Downtown Home')")
            
        # Description suggestions
        if description:
            word_count = len(re.findall(r'\b\w+\b', description))
            if word_count < 15:
                suggestions.append("📝 Description: Add details about materials needed, skill requirements, or project scope")
                
        # Image suggestions
        if image_count < 3:
            suggestions.append("📸 Images: Include photos showing the current state, specific problem areas, and desired outcome examples")
        elif image_count >= 3:
            suggestions.append("✅ Great job including multiple images! This helps contractors understand your project better.")
            
        return suggestions

class JobPostingEnhancer:
    """Enhances job postings with additional metadata and analysis"""
    
    def __init__(self):
        self.validator = JobRequirementsValidator()
        
    def analyze_job_complexity(self, title, description, budget=None):
        """Analyze and categorize job complexity"""
        complexity_score = 0
        factors = []
        
        # Analyze description complexity
        if description:
            words = re.findall(r'\b\w+\b', description.lower())
            word_count = len(words)
            
            if word_count > 50:
                complexity_score += 1
                factors.append("Detailed description")
                
            # Check for complex keywords
            complex_keywords = ['renovation', 'custom', 'design', 'structural', 'electrical', 'plumbing', 'permit', 'inspection']
            complex_count = sum(1 for keyword in complex_keywords if keyword in description.lower())
            
            if complex_count >= 3:
                complexity_score += 2
                factors.append("Multiple specialties required")
            elif complex_count >= 1:
                complexity_score += 1
                factors.append("Specialized skills needed")
                
        # Analyze budget
        if budget:
            try:
                budget_value = float(budget)
                if budget_value > 10000:
                    complexity_score += 2
                    factors.append("High-value project")
                elif budget_value > 2000:
                    complexity_score += 1
                    factors.append("Medium-value project")
            except (ValueError, TypeError):
                pass
                
        # Determine complexity level
        if complexity_score >= 4:
            level = "High"
        elif complexity_score >= 2:
            level = "Medium"
        else:
            level = "Low"
            
        return {
            'level': level,
            'score': complexity_score,
            'factors': factors
        }
    
    def suggest_contractor_categories(self, title, description):
        """Suggest relevant contractor categories based on job content"""
        categories = []
        
        text = f"{title} {description}".lower()
        
        # Category mapping
        category_keywords = {
            'plumbing': ['plumb', 'pipe', 'leak', 'drain', 'faucet', 'toilet', 'shower', 'sink', 'water'],
            'electrical': ['electric', 'wire', 'outlet', 'switch', 'light', 'panel', 'circuit', 'voltage'],
            'roofing': ['roof', 'shingle', 'gutter', 'leak', 'tile', 'metal', 'flat roof'],
            'flooring': ['floor', 'carpet', 'hardwood', 'tile', 'laminate', 'vinyl', 'marble'],
            'painting': ['paint', 'color', 'wall', 'ceiling', 'primer', 'brush', 'exterior', 'interior'],
            'landscaping': ['landscape', 'garden', 'lawn', 'tree', 'plant', 'irrigation', 'yard'],
            'kitchens': ['kitchen', 'cabinet', 'counter', 'appliance', 'sink', 'stove', 'refrigerator'],
            'bathrooms': ['bathroom', 'shower', 'tub', 'vanity', 'mirror', 'toilet'],
            'drywall': ['drywall', 'sheetrock', 'texture', 'mud', 'tape', 'patch'],
            'masonry': ['brick', 'stone', 'concrete', 'mortar', 'foundation', 'retaining wall'],
            'carpentry': ['wood', 'trim', 'cabinet', 'deck', 'frame', 'door', 'window'],
            'cleaning': ['clean', 'wash', 'detail', 'pressure wash', 'sanitize', 'deep clean']
        }
        
        for category, keywords in category_keywords.items():
            if any(keyword in text for keyword in keywords):
                categories.append(category)
                
        return categories[:5]  # Return top 5 matches
    
    def estimate_project_duration(self, complexity_analysis, suggested_categories):
        """Estimate project duration based on complexity and categories"""
        base_days = 1
        
        # Adjust based on complexity
        if complexity_analysis['level'] == 'High':
            base_days = 14
        elif complexity_analysis['level'] == 'Medium':
            base_days = 7
        else:
            base_days = 3
            
        # Adjust based on categories
        complex_categories = ['electrical', 'plumbing', 'roofing', 'kitchens', 'bathrooms']
        if any(cat in suggested_categories for cat in complex_categories):
            base_days *= 1.5
            
        if len(suggested_categories) > 2:
            base_days *= 1.3  # Multiple specialties
            
        return {
            'estimated_days': round(base_days),
            'range': f"{max(1, round(base_days * 0.7))}-{round(base_days * 1.3)} days"
        }

# Decorator for requiring enhanced job validation
def require_enhanced_validation(f):
    """Decorator to ensure job posts meet enhanced requirements"""
    from functools import wraps
    
    @wraps(f)
    def decorated_function(*args, **kwargs):
        from flask import request, flash, redirect, url_for
        
        if request.method == 'POST':
            validator = JobRequirementsValidator()
            
            title = request.form.get('title', '').strip()
            description = request.form.get('description', '').strip()
            images = request.files.getlist('images[]') if 'images[]' in request.files else []
            budget = request.form.get('budget')
            timeline = request.form.get('timeline', '').strip()
            
            is_valid, errors, warnings = validator.validate_job_posting(
                title, description, images, budget, timeline
            )
            
            if not is_valid:
                for error in errors:
                    flash(error, 'error')
                return redirect(request.url)
                
            # Add warnings as info messages
            for warning in warnings:
                flash(warning, 'warning')
                
        return f(*args, **kwargs)
    
    return decorated_function