from django.shortcuts import render, redirect
from django.http import HttpResponse
from django.contrib.auth import authenticate, login as auth_login, logout as auth_logout
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from .models import Profile
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak, HRFlowable
from io import BytesIO


def format_skills(text):
    if not text: return ""
    lines = []
    # Split by newline
    parts = [p.strip() for p in text.split('\n') if p.strip()]
    for part in parts:
        if ':' in part:
            key, val = part.split(':', 1)
            lines.append(f"<b>{key.strip()}:</b> {val.strip()}")
        else:
            lines.append(part)
    return '<br/>'.join(lines)



def home(request):
    return render(request, 'pdf/home.html')


def signup(request):
    if request.user.is_authenticated:
        return redirect('accept')
    
    if request.method == "POST":
        email = request.POST.get("email", "").strip()
        password1 = request.POST.get("password1", "")
        password2 = request.POST.get("password2", "")
        
        errors = {}
        
        # Validation
        if not email:
            errors['email'] = 'Email is required.'
        elif User.objects.filter(email=email).exists():
            errors['email'] = 'Email already exists!'
        
        if not password1:
            errors['password1'] = 'Password is required.'
        elif len(password1) < 8:
            errors['password1'] = 'Password must be at least 8 characters long.'
        
        if password1 != password2:
            errors['password2'] = 'Passwords do not match!'
        
        if errors:
            context = {
                'form': type('Form', (), {'non_field_errors': errors.values()})(),
            }
            return render(request, 'pdf/signup.html', context)
        
        # Create user with email-based username
        username = email.split('@')[0]  # Use part before @ as username
        counter = 1
        original_username = username
        while User.objects.filter(username=username).exists():
            username = f"{original_username}{counter}"
            counter += 1
        
        user = User.objects.create_user(username=username, email=email, password=password1)
        auth_login(request, user)
        
        # Initialize fresh session for CV creation
        request.session['step'] = 0
        request.session['template'] = 'modern'
        request.session['form_data'] = {}
        
        return redirect('accept')
    
    return render(request, 'pdf/signup.html')


def login_view(request):
    if request.user.is_authenticated:
        return redirect('accept')
    
    if request.method == "POST":
        email = request.POST.get("email", "").strip()
        password = request.POST.get("password", "")
        
        # Authenticate with email
        try:
            user_obj = User.objects.get(email=email)
            user = authenticate(request, username=user_obj.username, password=password)
        except User.DoesNotExist:
            user = None
        
        if user is not None:
            auth_login(request, user)
            
            # Initialize fresh session for CV creation
            request.session['step'] = 0
            request.session['template'] = 'modern'
            request.session['form_data'] = {}
            
            return redirect('accept')
        else:
            context = {
                'form': type('Form', (), {
                    'non_field_errors': ['Invalid email or password!']
                })()
            }
            return render(request, 'pdf/login.html', context)
    
    return render(request, 'pdf/login.html')


def logout_view(request):
    auth_logout(request)
    return redirect('home')


@login_required(login_url='login')
# Create your views here.
def accept(request):
    success = False
    profile = None
    step = request.session.get('step', 0)  # 0 = template selection
    preview = False
    template = request.session.get('template', 'modern')
    
    if request.method == "POST":
        # Template selection
        if "template" in request.POST:
            template = request.POST.get("template", "modern")
            request.session['template'] = template
            request.session['step'] = 1
            step = 1
            # Note: form_data is preserved when changing templates
        # Continue editing with current template
        elif "continue_editing" in request.POST:
            request.session['step'] = 1
            step = 1
        # Restart template selection (keeps data, allows template change)
        elif "restart_templates" in request.POST:
            request.session['step'] = 0
            step = 0
        # Clear all data and start fresh
        elif "start_fresh" in request.POST:
            request.session['step'] = 0
            request.session['form_data'] = {}
            request.session['template'] = 'modern'
            step = 0
        else:
            current_step = int(request.POST.get("step", 1))
            
            # Get all form data from session or POST
            if 'form_data' not in request.session:
                request.session['form_data'] = {}
            
            form_data = request.session['form_data']
            
            # Update with current step data
            if current_step == 1:
                # Combined: Name, Contact Info, and Social Profiles
                form_data['name'] = request.POST.get("name", "")
                form_data['email'] = request.POST.get("email", "")
                form_data['phone'] = request.POST.get("phone", "")
                form_data['github_url'] = request.POST.get("github_url", "")
                form_data['linkedin_url'] = request.POST.get("linkedin_url", "")
            elif current_step == 2:
                form_data['summary'] = request.POST.get("summary", "")
            elif current_step == 3:
                projects_list = []
                projects_count = int(request.POST.get("projects_count", 1))
                for i in range(projects_count):
                    title = request.POST.get(f"project_title_{i}", "")
                    points = request.POST.get(f"project_points_{i}", "")
                    if title.strip() or points.strip():
                        projects_list.append({"title": title, "points": points})
                form_data['projects_list'] = projects_list
                # Build flat string for backward compatibility
                flat_projects = []
                for p in projects_list:
                    flat_projects.append(p['title'])
                    for line in p['points'].split('\n'):
                        if line.strip():
                            flat_projects.append(f"• {line.strip()}")
                form_data['projects'] = '\n'.join(flat_projects)
            elif current_step == 4:
                form_data['skills'] = request.POST.get("skills", "")
            elif current_step == 5:
                education_list = []
                education_count = int(request.POST.get("education_count", 1))
                for i in range(education_count):
                    degree = request.POST.get(f"degree_{i}", "")
                    university = request.POST.get(f"university_{i}", "")
                    if degree.strip() or university.strip():
                        education_list.append({"degree": degree, "university": university})
                form_data['education_list'] = education_list
                # Backward compat
                if education_list:
                    form_data['degree'] = education_list[0].get('degree', '')
                    form_data['university'] = education_list[0].get('university', '')
            elif current_step == 6:
                form_data['certifications'] = request.POST.get("certifications", "")
            
            request.session['form_data'] = form_data
            
            # Check if user wants to preview
            if "preview" in request.POST:
                preview = True
                step = 7
            # Check if this is the final submission
            elif "submit" in request.POST:
                # Save to database
                degree = ""
                university = ""
                if form_data.get('education_list'):
                    degree = form_data['education_list'][0].get('degree', '')
                    university = form_data['education_list'][0].get('university', '')
                profile = Profile(
                    name=form_data.get('name', ''),
                    email=form_data.get('email', ''),
                    phone=form_data.get('phone', ''),
                    github_url=form_data.get('github_url', ''),
                    linkedin_url=form_data.get('linkedin_url', ''),
                    summary=form_data.get('summary', ''),
                    degree=degree,
                    university=university,
                    projects=form_data.get('projects', ''),
                    skills=form_data.get('skills', ''),
                    certifications=form_data.get('certifications', '')
                )
                profile.save()
                # Set step to 8 for celebration screen
                step = 8
                request.session['step'] = 8
            else:
                # Move to next or previous step
                if "next_step" in request.POST:
                    step = int(request.POST.get("next_step"))
                elif "previous_step" in request.POST:
                    step = int(request.POST.get("previous_step"))
                else:
                    step = current_step
                request.session['step'] = step
    
    # Get saved form data from session
    form_data = request.session.get('form_data', {})
    # Build points_list for each project so template can iterate
    if 'projects_list' in form_data:
        for proj in form_data['projects_list']:
            proj['points_list'] = [line.strip() for line in proj.get('points', '').split('\n') if line.strip()]
    # Check if there's existing data
    has_previous_data = bool(form_data and any(form_data.values()))
    
    return render(request, 'pdf/accept.html', {
        'success': success,
        'profile': profile,
        'step': step,
        'form_data': form_data,
        'preview': preview,
        'template': template,
        'has_previous_data': has_previous_data
    })


def generate_pdf(request, profile_id):
    profile = Profile.objects.get(id=profile_id)
    template = request.session.get('template', 'modern')
    
    if template == 'classic':
        return generate_classic_pdf(profile)
    elif template == 'modern':
        return generate_modern_pdf(profile)
    elif template == 'minimal':
        return generate_minimal_pdf(profile)
    elif template == 'altacv':
        return generate_altacv_pdf(profile)
    elif template == 'curve':
        return generate_curve_pdf(profile)
    elif template == 'hipster':
        return generate_hipster_pdf(profile)
    else:
        return generate_professional_pdf(profile)


def generate_classic_pdf(profile):
    """Classic black & white traditional format"""
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter,
                           rightMargin=0.5*inch, leftMargin=0.5*inch,
                           topMargin=0.5*inch, bottomMargin=0.5*inch)
    elements = []
    styles = getSampleStyleSheet()
    
    # Header style
    name_style = ParagraphStyle('NameStyle', parent=styles['Heading1'],
                                fontSize=20, textColor='#000000',
                                alignment=1, spaceAfter=2, fontName='Helvetica-Bold')
    contact_style = ParagraphStyle('ContactStyle', parent=styles['Normal'],
                                   fontSize=9, alignment=1, spaceAfter=12)
    section_style = ParagraphStyle('SectionStyle', parent=styles['Heading2'],
                                   fontSize=11, textColor='#000000', spaceAfter=8,
                                   spaceBefore=8, fontName='Helvetica-Bold')
    body_style = ParagraphStyle('BodyStyle', parent=styles['Normal'],
                                fontSize=10, spaceAfter=4, alignment=4)
    bullet_style = ParagraphStyle('BulletStyle', parent=styles['Normal'],
                                  fontSize=10, leftIndent=20, spaceAfter=3, alignment=4)
    
    # Header - Name + Contact merged
    elements.append(Paragraph(profile.name.upper(), name_style))
    contact_parts = [profile.email, profile.phone]
    if profile.github_url:
        contact_parts.append(f'<a href="{profile.github_url}" color="#667eea">GitHub</a>')
    if profile.linkedin_url:
        contact_parts.append(f'<a href="{profile.linkedin_url}" color="#667eea">LinkedIn</a>')
    elements.append(Paragraph(' &nbsp;|&nbsp; '.join(contact_parts), contact_style))
    elements.append(HRFlowable(width='100%', thickness=1.5, color='#000000', spaceAfter=10, spaceBefore=4))
    
    # Professional Summary
    if profile.summary.strip():
        elements.append(Paragraph("PROFESSIONAL SUMMARY", section_style))
        elements.append(Paragraph(profile.summary, body_style))
        elements.append(Spacer(1, 0.1*inch))
    
    # Education
    elements.append(Paragraph("EDUCATION", section_style))
    education = f"<b>{profile.degree}</b> | {profile.university}"
    elements.append(Paragraph(education, body_style))
    elements.append(Spacer(1, 0.1*inch))
    
    # Projects
    if profile.projects.strip():
        elements.append(Paragraph("PROJECTS", section_style))
        for proj in profile.projects.split('\n'):
            if proj.strip():
                elements.append(Paragraph(f"• {proj.strip()}", bullet_style))
        elements.append(Spacer(1, 0.1*inch))
    
    # Skills
    if profile.skills.strip():
        elements.append(Paragraph("TECHNICAL SKILLS", section_style))
        elements.append(Paragraph(format_skills(profile.skills), body_style))
    
    
    if profile.certifications.strip():
        elements.append(Paragraph("CERTIFICATIONS", section_style))
        # Handle newlines for certifications if needed, but Paragraph handles text wrap.
        # If user used newlines, we might want to preserve them.
        # profile.certifications is a TextField.
        # Replacing newlines with <br/> for Paragraph compatibility.
        cert_text = profile.certifications.replace('\n', '<br/>')
        elements.append(Paragraph(cert_text, body_style))
        elements.append(Spacer(1, 0.1*inch))
    doc.build(elements)
    buffer.seek(0)
    response = HttpResponse(buffer.getvalue(), content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="CV_{profile.name}_Classic.pdf"'
    return response


def generate_modern_pdf(profile):
    """Modern format with accent color"""
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter,
                           rightMargin=0.6*inch, leftMargin=0.6*inch,
                           topMargin=0.6*inch, bottomMargin=0.6*inch)
    elements = []
    styles = getSampleStyleSheet()
    
    name_style = ParagraphStyle('NameStyle', parent=styles['Heading1'],
                                fontSize=22, textColor='#667eea',
                                alignment=0, spaceAfter=2, fontName='Helvetica-Bold')
    contact_style = ParagraphStyle('ContactStyle', parent=styles['Normal'],
                                   fontSize=9, textColor='#333333', spaceAfter=12)
    section_style = ParagraphStyle('SectionStyle', parent=styles['Heading2'],
                                   fontSize=12, textColor='#667eea', spaceAfter=10,
                                   spaceBefore=10, fontName='Helvetica-Bold')
    body_style = ParagraphStyle('BodyStyle', parent=styles['Normal'],
                                fontSize=10, spaceAfter=4, alignment=4)
    bullet_style = ParagraphStyle('BulletStyle', parent=styles['Normal'],
                                  fontSize=10, leftIndent=20, spaceAfter=3, alignment=4)
    
    # Header - Name + Contact merged
    elements.append(Paragraph(profile.name.upper(), name_style))
    contact_parts = [profile.email, profile.phone]
    if profile.github_url:
        contact_parts.append(f'<a href="{profile.github_url}" color="#667eea">GitHub</a>')
    if profile.linkedin_url:
        contact_parts.append(f'<a href="{profile.linkedin_url}" color="#667eea">LinkedIn</a>')
    elements.append(Paragraph(' &nbsp;|&nbsp; '.join(contact_parts), contact_style))
    elements.append(HRFlowable(width='100%', thickness=1.5, color='#667eea', spaceAfter=10, spaceBefore=4))
    
    if profile.summary.strip():
        elements.append(Paragraph("PROFESSIONAL SUMMARY", section_style))
        elements.append(Paragraph(profile.summary, body_style))
        elements.append(Spacer(1, 0.15*inch))
    
    elements.append(Paragraph("EDUCATION", section_style))
    education = f"<b>{profile.degree}</b><br/>{profile.university}"
    elements.append(Paragraph(education, body_style))
    elements.append(Spacer(1, 0.15*inch))
    
    if profile.projects.strip():
        elements.append(Paragraph("PROJECTS", section_style))
        for proj in profile.projects.split('\n'):
            if proj.strip():
                elements.append(Paragraph(f"▪ {proj.strip()}", bullet_style))
        elements.append(Spacer(1, 0.15*inch))
    
    if profile.skills.strip():
        elements.append(Paragraph("TECHNICAL SKILLS", section_style))
        elements.append(Paragraph(format_skills(profile.skills), body_style))
    
    
    if profile.certifications.strip():
        elements.append(Paragraph("CERTIFICATIONS", section_style))
        # Handle newlines for certifications if needed, but Paragraph handles text wrap.
        # If user used newlines, we might want to preserve them.
        # profile.certifications is a TextField.
        # Replacing newlines with <br/> for Paragraph compatibility.
        cert_text = profile.certifications.replace('\n', '<br/>')
        elements.append(Paragraph(cert_text, body_style))
        elements.append(Spacer(1, 0.15*inch))
    doc.build(elements)
    buffer.seek(0)
    response = HttpResponse(buffer.getvalue(), content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="CV_{profile.name}_Modern.pdf"'
    return response


def generate_minimal_pdf(profile):
    """Minimal clean design"""
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter,
                           rightMargin=0.75*inch, leftMargin=0.75*inch,
                           topMargin=0.75*inch, bottomMargin=0.75*inch)
    elements = []
    styles = getSampleStyleSheet()
    
    name_style = ParagraphStyle('NameStyle', parent=styles['Heading1'],
                                fontSize=18, textColor='#000000',
                                alignment=1, spaceAfter=4, fontName='Helvetica-Bold')
    contact_style = ParagraphStyle('ContactStyle', parent=styles['Normal'],
                                   fontSize=8, alignment=1, spaceAfter=16)
    section_style = ParagraphStyle('SectionStyle', parent=styles['Heading2'],
                                   fontSize=11, textColor='#000000', spaceAfter=8,
                                   spaceBefore=12, fontName='Helvetica-Bold')
    body_style = ParagraphStyle('BodyStyle', parent=styles['Normal'],
                                fontSize=10, spaceAfter=4, alignment=4)
    bullet_style = ParagraphStyle('BulletStyle', parent=styles['Normal'],
                                  fontSize=10, leftIndent=15, spaceAfter=2, alignment=4)
    
    elements.append(Paragraph(profile.name.upper(), name_style))
    contact_parts = [profile.email, profile.phone]
    if profile.github_url:
        contact_parts.append(f'<a href="{profile.github_url}" color="#555555">GitHub</a>')
    if profile.linkedin_url:
        contact_parts.append(f'<a href="{profile.linkedin_url}" color="#555555">LinkedIn</a>')
    elements.append(Paragraph(' • '.join(contact_parts), contact_style))
    elements.append(HRFlowable(width='100%', thickness=0.5, color='#000000', spaceAfter=10, spaceBefore=4))
    
    if profile.summary.strip():
        elements.append(Paragraph("SUMMARY", section_style))
        elements.append(Paragraph(profile.summary, body_style))
        elements.append(Spacer(1, 0.1*inch))
    
    elements.append(Paragraph("EDUCATION", section_style))
    education = f"{profile.degree} — {profile.university}"
    elements.append(Paragraph(education, body_style))
    elements.append(Spacer(1, 0.1*inch))
    
    if profile.projects.strip():
        elements.append(Paragraph("PROJECTS", section_style))
        for proj in profile.projects.split('\n'):
            if proj.strip():
                elements.append(Paragraph(f"• {proj.strip()}", bullet_style))
        elements.append(Spacer(1, 0.1*inch))
    
    if profile.skills.strip():
        elements.append(Paragraph("SKILLS", section_style))
        elements.append(Paragraph(format_skills(profile.skills), body_style))
    
    
    if profile.certifications.strip():
        elements.append(Paragraph("CERTIFICATIONS", section_style))
        # Handle newlines for certifications if needed, but Paragraph handles text wrap.
        # If user used newlines, we might want to preserve them.
        # profile.certifications is a TextField.
        # Replacing newlines with <br/> for Paragraph compatibility.
        cert_text = profile.certifications.replace('\n', '<br/>')
        elements.append(Paragraph(cert_text, body_style))
        elements.append(Spacer(1, 0.1*inch))
    doc.build(elements)
    buffer.seek(0)
    response = HttpResponse(buffer.getvalue(), content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="CV_{profile.name}_Minimal.pdf"'
    return response


def generate_professional_pdf(profile):
    """Professional format with lines"""
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter,
                           rightMargin=0.5*inch, leftMargin=0.5*inch,
                           topMargin=0.5*inch, bottomMargin=0.5*inch)
    elements = []
    styles = getSampleStyleSheet()
    
    name_style = ParagraphStyle('NameStyle', parent=styles['Heading1'],
                                fontSize=20, textColor='#1a1a1a',
                                alignment=0, spaceAfter=0, fontName='Helvetica-Bold')
    contact_style = ParagraphStyle('ContactStyle', parent=styles['Normal'],
                                   fontSize=9, spaceAfter=12)
    section_style = ParagraphStyle('SectionStyle', parent=styles['Heading2'],
                                   fontSize=12, textColor='#1a1a1a', spaceAfter=8,
                                   spaceBefore=10, fontName='Helvetica-Bold',
                                   borderBottomWidth=1.5, borderBottomColor='#1a1a1a')
    body_style = ParagraphStyle('BodyStyle', parent=styles['Normal'],
                                fontSize=10, spaceAfter=5, alignment=4)
    bullet_style = ParagraphStyle('BulletStyle', parent=styles['Normal'],
                                  fontSize=10, leftIndent=20, spaceAfter=3, alignment=4)
    
    elements.append(Paragraph(profile.name.upper(), name_style))
    contact_parts = [profile.email, profile.phone]
    if profile.github_url:
        contact_parts.append(f'<a href="{profile.github_url}" color="#1a1a1a">GitHub</a>')
    if profile.linkedin_url:
        contact_parts.append(f'<a href="{profile.linkedin_url}" color="#1a1a1a">LinkedIn</a>')
    elements.append(Paragraph(' &nbsp;|&nbsp; '.join(contact_parts), contact_style))
    elements.append(HRFlowable(width='100%', thickness=1.5, color='#1a1a1a', spaceAfter=10, spaceBefore=4))
    
    if profile.summary.strip():
        elements.append(Paragraph("PROFESSIONAL PROFILE", section_style))
        elements.append(Paragraph(profile.summary, body_style))
        elements.append(Spacer(1, 0.12*inch))
    
    elements.append(Paragraph("EDUCATION", section_style))
    education = f"<b>{profile.degree}</b><br/>{profile.university}"
    elements.append(Paragraph(education, body_style))
    elements.append(Spacer(1, 0.12*inch))
    
    if profile.projects.strip():
        elements.append(Paragraph("PROJECTS & EXPERIENCE", section_style))
        for proj in profile.projects.split('\n'):
            if proj.strip():
                elements.append(Paragraph(f"◆ {proj.strip()}", bullet_style))
        elements.append(Spacer(1, 0.12*inch))
    
    if profile.skills.strip():
        elements.append(Paragraph("TECHNICAL SKILLS", section_style))
        elements.append(Paragraph(format_skills(profile.skills), body_style))
    
    
    if profile.certifications.strip():
        elements.append(Paragraph("CERTIFICATIONS", section_style))
        # Handle newlines for certifications if needed, but Paragraph handles text wrap.
        # If user used newlines, we might want to preserve them.
        # profile.certifications is a TextField.
        # Replacing newlines with <br/> for Paragraph compatibility.
        cert_text = profile.certifications.replace('\n', '<br/>')
        elements.append(Paragraph(cert_text, body_style))
        elements.append(Spacer(1, 0.12*inch))
    doc.build(elements)
    buffer.seek(0)
    response = HttpResponse(buffer.getvalue(), content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="CV_{profile.name}_Professional.pdf"'
    return response


def generate_altacv_pdf(profile):
    """AltaCV style - Sidebar layout with achievements"""
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter,
                           rightMargin=0.4*inch, leftMargin=0.4*inch,
                           topMargin=0.4*inch, bottomMargin=0.4*inch)
    elements = []
    styles = getSampleStyleSheet()
    
    name_style = ParagraphStyle('NameStyle', parent=styles['Heading1'],
                                fontSize=22, textColor='#667eea',
                                spaceAfter=2, fontName='Helvetica-Bold')
    section_style = ParagraphStyle('SectionStyle', parent=styles['Heading2'],
                                   fontSize=12, textColor='#667eea', spaceAfter=8,
                                   spaceBefore=6, fontName='Helvetica-Bold')
    body_style = ParagraphStyle('BodyStyle', parent=styles['Normal'],
                                fontSize=10, spaceAfter=4)
    
    elements.append(Paragraph(profile.name.upper(), name_style))
    contact_parts = [profile.email, profile.phone]
    if profile.github_url:
        contact_parts.append(f'<a href="{profile.github_url}" color="#667eea">GitHub</a>')
    if profile.linkedin_url:
        contact_parts.append(f'<a href="{profile.linkedin_url}" color="#667eea">LinkedIn</a>')
    elements.append(Paragraph(' &nbsp;|&nbsp; '.join(contact_parts), body_style))
    elements.append(HRFlowable(width='100%', thickness=1.5, color='#667eea', spaceAfter=10, spaceBefore=4))
    
    if profile.summary.strip():
        elements.append(Paragraph("PROFESSIONAL SUMMARY", section_style))
        elements.append(Paragraph(profile.summary, body_style))
        elements.append(Spacer(1, 0.1*inch))
    
    elements.append(Paragraph("EXPERIENCE", section_style))
    elements.append(Paragraph(profile.projects if profile.projects.strip() else "Professional experience and achievements", body_style))
    elements.append(Spacer(1, 0.1*inch))
    
    elements.append(Paragraph("EDUCATION", section_style))
    education = f"<b>{profile.degree}</b> | {profile.university}"
    elements.append(Paragraph(education, body_style))
    elements.append(Spacer(1, 0.1*inch))
    
    if profile.skills.strip():
        elements.append(Paragraph("SKILLS", section_style))
        elements.append(Paragraph(format_skills(profile.skills), body_style))
    
    
    if profile.certifications.strip():
        elements.append(Paragraph("CERTIFICATIONS", section_style))
        # Handle newlines for certifications if needed, but Paragraph handles text wrap.
        # If user used newlines, we might want to preserve them.
        # profile.certifications is a TextField.
        # Replacing newlines with <br/> for Paragraph compatibility.
        cert_text = profile.certifications.replace('\n', '<br/>')
        elements.append(Paragraph(cert_text, body_style))
        elements.append(Spacer(1, 0.1*inch))
    doc.build(elements)
    buffer.seek(0)
    response = HttpResponse(buffer.getvalue(), content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="CV_{profile.name}_AltaCV.pdf"'
    return response


def generate_curve_pdf(profile):
    """CurVe CV - Modern colorful sections"""
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter,
                           rightMargin=0.5*inch, leftMargin=0.5*inch,
                           topMargin=0.5*inch, bottomMargin=0.5*inch)
    elements = []
    styles = getSampleStyleSheet()
    
    name_style = ParagraphStyle('NameStyle', parent=styles['Heading1'],
                                fontSize=20, textColor='#ff6b6b',
                                spaceAfter=4, fontName='Helvetica-Bold')
    section_style = ParagraphStyle('SectionStyle', parent=styles['Heading2'],
                                   fontSize=12, textColor='#4ecdc4', spaceAfter=8,
                                   spaceBefore=8, fontName='Helvetica-Bold')
    body_style = ParagraphStyle('BodyStyle', parent=styles['Normal'],
                                fontSize=10, spaceAfter=4)
    
    elements.append(Paragraph(profile.name.upper(), name_style))
    contact_parts = [profile.email, profile.phone]
    if profile.github_url:
        contact_parts.append(f'<a href="{profile.github_url}" color="#ff6b6b">GitHub</a>')
    if profile.linkedin_url:
        contact_parts.append(f'<a href="{profile.linkedin_url}" color="#ff6b6b">LinkedIn</a>')
    elements.append(Paragraph(' &nbsp;|&nbsp; '.join(contact_parts), body_style))
    elements.append(HRFlowable(width='100%', thickness=1.5, color='#4ecdc4', spaceAfter=10, spaceBefore=4))
    
    if profile.summary.strip():
        elements.append(Paragraph("PROFESSIONAL PROFILE", section_style))
        elements.append(Paragraph(profile.summary, body_style))
        elements.append(Spacer(1, 0.1*inch))
    
    elements.append(Paragraph("EMPLOYMENT HISTORY", section_style))
    elements.append(Paragraph(profile.projects if profile.projects.strip() else "Professional background and experience", body_style))
    elements.append(Spacer(1, 0.1*inch))
    
    elements.append(Paragraph("EDUCATION", section_style))
    education = f"<b>{profile.degree}</b><br/>{profile.university}"
    elements.append(Paragraph(education, body_style))
    elements.append(Spacer(1, 0.1*inch))
    
    if profile.skills.strip():
        elements.append(Paragraph("TECHNICAL COMPETENCIES", section_style))
        elements.append(Paragraph(format_skills(profile.skills), body_style))
    
    
    if profile.certifications.strip():
        elements.append(Paragraph("CERTIFICATIONS", section_style))
        # Handle newlines for certifications if needed, but Paragraph handles text wrap.
        # If user used newlines, we might want to preserve them.
        # profile.certifications is a TextField.
        # Replacing newlines with <br/> for Paragraph compatibility.
        cert_text = profile.certifications.replace('\n', '<br/>')
        elements.append(Paragraph(cert_text, body_style))
        elements.append(Spacer(1, 0.1*inch))
    doc.build(elements)
    buffer.seek(0)
    response = HttpResponse(buffer.getvalue(), content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="CV_{profile.name}_CurVe.pdf"'
    return response


def generate_hipster_pdf(profile):
    """Hipster CV - Dark header with modern layout"""
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter,
                           rightMargin=0.5*inch, leftMargin=0.5*inch,
                           topMargin=0.5*inch, bottomMargin=0.5*inch)
    elements = []
    styles = getSampleStyleSheet()
    
    name_style = ParagraphStyle('NameStyle', parent=styles['Heading1'],
                                fontSize=22, textColor='#2c3e50',
                                spaceAfter=3, fontName='Helvetica-Bold',
                                alignment=1)
    subtitle_style = ParagraphStyle('SubtitleStyle', parent=styles['Normal'],
                                    fontSize=11, textColor='#34495e',
                                    spaceAfter=4, alignment=1)
    section_style = ParagraphStyle('SectionStyle', parent=styles['Heading2'],
                                   fontSize=11, textColor='#2c3e50', spaceAfter=8,
                                   spaceBefore=8, fontName='Helvetica-Bold',
                                   borderColor='#34495e', borderPadding=4,
                                   borderWidth=0.5)
    body_style = ParagraphStyle('BodyStyle', parent=styles['Normal'],
                                fontSize=10, spaceAfter=4)
    
    elements.append(Paragraph(profile.name.upper(), name_style))
    elements.append(Paragraph("Professional Resume", subtitle_style))
    contact_parts = [profile.email, profile.phone]
    if profile.github_url:
        contact_parts.append(f'<a href="{profile.github_url}" color="#2c3e50">GitHub</a>')
    if profile.linkedin_url:
        contact_parts.append(f'<a href="{profile.linkedin_url}" color="#2c3e50">LinkedIn</a>')
    elements.append(Paragraph(' &nbsp;|&nbsp; '.join(contact_parts), body_style))
    elements.append(HRFlowable(width='100%', thickness=1, color='#2c3e50', spaceAfter=10, spaceBefore=4))
    
    if profile.summary.strip():
        elements.append(Paragraph("ABOUT", section_style))
        elements.append(Paragraph(profile.summary, body_style))
        elements.append(Spacer(1, 0.1*inch))
    
    elements.append(Paragraph("EXPERIENCE", section_style))
    if profile.projects.strip():
        for proj in profile.projects.split('\n'):
            if proj.strip():
                elements.append(Paragraph(f"• {proj.strip()}", body_style))
    else:
        elements.append(Paragraph("Professional work experience and achievements", body_style))
    elements.append(Spacer(1, 0.1*inch))
    
    elements.append(Paragraph("EDUCATION", section_style))
    education = f"<b>{profile.degree}</b> from {profile.university}"
    elements.append(Paragraph(education, body_style))
    elements.append(Spacer(1, 0.1*inch))
    
    if profile.skills.strip():
        elements.append(Paragraph("SKILLS", section_style))
        elements.append(Paragraph(format_skills(profile.skills), body_style))
    
    
    if profile.certifications.strip():
        elements.append(Paragraph("CERTIFICATIONS", section_style))
        # Handle newlines for certifications if needed, but Paragraph handles text wrap.
        # If user used newlines, we might want to preserve them.
        # profile.certifications is a TextField.
        # Replacing newlines with <br/> for Paragraph compatibility.
        cert_text = profile.certifications.replace('\n', '<br/>')
        elements.append(Paragraph(cert_text, body_style))
        elements.append(Spacer(1, 0.1*inch))
    doc.build(elements)
    buffer.seek(0)
    response = HttpResponse(buffer.getvalue(), content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="CV_{profile.name}_Hipster.pdf"'
    return response