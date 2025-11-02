/**
 * Swipe System JavaScript - Dating app style matching for LaborLooker
 * Handles card swiping, animations, and match detection
 */

let currentCards = [];
let currentCardIndex = 0;
let isDragging = false;
let startX = 0;
let startY = 0;
let currentX = 0;
let currentY = 0;

// Initialize the swipe system
function initializeSwipeSystem() {
    console.log('Initializing swipe system...');
    setupTouchEvents();
    setupKeyboardEvents();
}

// Load initial set of cards
function loadInitialCards() {
    const userType = document.body.dataset.userType || 'customer';
    const endpoint = userType === 'customer' ? '/api/swipe/contractors' : '/api/swipe/jobs';
    
    fetch(endpoint, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify(getFilterParams())
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            currentCards = data.cards;
            currentCardIndex = 0;
            renderCards();
            document.getElementById('loadingSpinner').style.display = 'none';
        } else {
            showError('Failed to load matches');
        }
    })
    .catch(error => {
        console.error('Error loading cards:', error);
        showError('Error loading matches');
    });
}

// Render cards in the swipe container
function renderCards() {
    const container = document.getElementById('swipeContainer');
    container.innerHTML = '';
    
    if (currentCards.length === 0) {
        showNoMoreCards();
        return;
    }
    
    // Show up to 3 cards at once (current + 2 behind)
    for (let i = 0; i < Math.min(3, currentCards.length - currentCardIndex); i++) {
        const cardIndex = currentCardIndex + i;
        const card = createCardElement(currentCards[cardIndex], i);
        container.appendChild(card);
    }
}

// Create a single card element
function createCardElement(cardData, stackIndex) {
    const card = document.createElement('div');
    card.className = 'swipe-card';
    card.style.zIndex = 10 - stackIndex;
    card.style.transform = `scale(${1 - stackIndex * 0.05}) translateY(${stackIndex * 10}px)`;
    
    const userType = document.body.dataset.userType || 'customer';
    
    card.innerHTML = `
        <div class="card-content" data-card-id="${cardData.id}">
            <div class="swipe-indicator indicator-pass">PASS</div>
            <div class="swipe-indicator indicator-like">LIKE</div>
            <div class="swipe-indicator indicator-super">SUPER!</div>
            
            ${userType === 'customer' ? renderContractorCard(cardData) : renderJobCard(cardData)}
        </div>
    `;
    
    if (stackIndex === 0) {
        setupCardEvents(card);
    }
    
    return card;
}

// Render contractor card for customers
function renderContractorCard(contractor) {
    const services = contractor.services ? contractor.services.split(',').slice(0, 3) : [];
    const rating = contractor.average_rating || 0;
    const reviewCount = contractor.total_ratings || 0;
    
    return `
        <div class="profile-image flex items-center justify-center">
            <div class="text-center text-white">
                <i class="fas fa-hard-hat text-6xl mb-2"></i>
                <h3 class="text-xl font-bold">${contractor.business_name}</h3>
            </div>
        </div>
        
        <div class="p-6">
            <div class="mb-4">
                <h2 class="text-2xl font-bold text-gray-800 mb-1">${contractor.business_name}</h2>
                <p class="text-gray-600">${contractor.contact_name}</p>
                <p class="text-sm text-gray-500 flex items-center mt-1">
                    <i class="fas fa-map-marker-alt mr-1"></i>
                    ${contractor.location} • ${contractor.geographic_area}
                </p>
            </div>
            
            <div class="mb-4">
                <div class="flex items-center mb-2">
                    <div class="rating-stars mr-2">
                        ${generateStarRating(rating)}
                    </div>
                    <span class="text-sm text-gray-600">${rating.toFixed(1)} (${reviewCount} reviews)</span>
                </div>
            </div>
            
            <div class="mb-4">
                <h4 class="font-semibold text-gray-700 mb-2">Services:</h4>
                <div class="flex flex-wrap gap-2">
                    ${services.map(service => `
                        <span class="bg-blue-100 text-blue-800 text-xs px-2 py-1 rounded-full">
                            ${service.trim()}
                        </span>
                    `).join('')}
                </div>
            </div>
            
            <div class="mb-4">
                <h4 class="font-semibold text-gray-700 mb-2">Experience:</h4>
                <p class="text-sm text-gray-600">${contractor.experience_level || 'Professional'}</p>
            </div>
            
            ${contractor.billing_plan ? `
                <div class="mb-4">
                    <h4 class="font-semibold text-gray-700 mb-2">Pricing:</h4>
                    <p class="text-sm text-gray-600">
                        ${contractor.billing_plan === 'commission_only' ? '10% Commission' : '5% Commission + $30/mo'}
                    </p>
                </div>
            ` : ''}
            
            <div class="text-center mt-6 text-sm text-gray-500">
                <p>Swipe right to connect • Swipe up for priority match</p>
            </div>
        </div>
    `;
}

// Render job card for contractors
function renderJobCard(job) {
    const payDisplay = job.pay_type === 'hourly' ? 
        `$${job.pay_amount}/hr` : 
        job.pay_range_min ? 
            `$${job.pay_range_min} - $${job.pay_range_max}` : 
            `$${job.pay_amount}`;
    
    return `
        <div class="profile-image flex items-center justify-center">
            <div class="text-center text-white">
                <i class="fas fa-briefcase text-6xl mb-2"></i>
                <h3 class="text-xl font-bold">${job.title}</h3>
            </div>
        </div>
        
        <div class="p-6">
            <div class="mb-4">
                <h2 class="text-2xl font-bold text-gray-800 mb-1">${job.title}</h2>
                <p class="text-gray-600">${job.labor_category}</p>
                <p class="text-sm text-gray-500 flex items-center mt-1">
                    <i class="fas fa-map-marker-alt mr-1"></i>
                    ${job.location}
                </p>
            </div>
            
            <div class="mb-4">
                <div class="flex items-center justify-between mb-2">
                    <span class="font-semibold text-green-600 text-lg">${payDisplay}</span>
                    <span class="bg-blue-100 text-blue-800 text-xs px-2 py-1 rounded-full">
                        ${job.job_type || 'Contract'}
                    </span>
                </div>
            </div>
            
            <div class="mb-4">
                <h4 class="font-semibold text-gray-700 mb-2">Description:</h4>
                <p class="text-sm text-gray-600 line-clamp-3">${job.description}</p>
            </div>
            
            <div class="mb-4">
                <h4 class="font-semibold text-gray-700 mb-2">Experience Required:</h4>
                <p class="text-sm text-gray-600 capitalize">${job.experience_level}</p>
            </div>
            
            ${job.requirements ? `
                <div class="mb-4">
                    <h4 class="font-semibold text-gray-700 mb-2">Requirements:</h4>
                    <p class="text-sm text-gray-600 line-clamp-2">${job.requirements}</p>
                </div>
            ` : ''}
            
            <div class="text-center mt-6 text-sm text-gray-500">
                <p>Swipe right to apply • Swipe up for priority application</p>
            </div>
        </div>
    `;
}

// Generate star rating HTML
function generateStarRating(rating) {
    const fullStars = Math.floor(rating);
    const hasHalfStar = rating % 1 >= 0.5;
    const emptyStars = 5 - fullStars - (hasHalfStar ? 1 : 0);
    
    let html = '';
    for (let i = 0; i < fullStars; i++) {
        html += '<i class="fas fa-star"></i>';
    }
    if (hasHalfStar) {
        html += '<i class="fas fa-star-half-alt"></i>';
    }
    for (let i = 0; i < emptyStars; i++) {
        html += '<i class="far fa-star"></i>';
    }
    
    return html;
}

// Setup touch and mouse events for card swiping
function setupCardEvents(card) {
    const cardContent = card.querySelector('.card-content');
    
    // Mouse events
    cardContent.addEventListener('mousedown', handleStart);
    document.addEventListener('mousemove', handleMove);
    document.addEventListener('mouseup', handleEnd);
    
    // Touch events
    cardContent.addEventListener('touchstart', handleStart, { passive: false });
    document.addEventListener('touchmove', handleMove, { passive: false });
    document.addEventListener('touchend', handleEnd);
}

// Handle start of drag/swipe
function handleStart(e) {
    e.preventDefault();
    isDragging = true;
    
    const clientX = e.clientX || e.touches[0].clientX;
    const clientY = e.clientY || e.touches[0].clientY;
    
    startX = clientX;
    startY = clientY;
    currentX = clientX;
    currentY = clientY;
    
    const card = e.target.closest('.swipe-card');
    if (card) {
        card.classList.add('dragging');
    }
}

// Handle drag/swipe movement
function handleMove(e) {
    if (!isDragging) return;
    
    e.preventDefault();
    
    const clientX = e.clientX || e.touches[0].clientX;
    const clientY = e.clientY || e.touches[0].clientY;
    
    currentX = clientX;
    currentY = clientY;
    
    const deltaX = currentX - startX;
    const deltaY = currentY - startY;
    
    const card = document.querySelector('.swipe-card.dragging .card-content');
    if (!card) return;
    
    const rotation = deltaX * 0.1;
    const scale = Math.max(0.8, 1 - Math.abs(deltaX) * 0.0005);
    
    card.style.transform = `translateX(${deltaX}px) translateY(${deltaY}px) rotate(${rotation}deg) scale(${scale})`;
    card.style.opacity = Math.max(0.3, 1 - Math.abs(deltaX) * 0.002);
    
    // Show swipe indicators
    const indicators = card.querySelectorAll('.swipe-indicator');
    indicators.forEach(indicator => indicator.classList.remove('show'));
    
    if (Math.abs(deltaX) > 50 || Math.abs(deltaY) > 50) {
        if (deltaY < -80) {
            card.querySelector('.indicator-super').classList.add('show');
        } else if (deltaX > 80) {
            card.querySelector('.indicator-like').classList.add('show');
        } else if (deltaX < -80) {
            card.querySelector('.indicator-pass').classList.add('show');
        }
    }
}

// Handle end of drag/swipe
function handleEnd(e) {
    if (!isDragging) return;
    
    isDragging = false;
    
    const card = document.querySelector('.swipe-card.dragging');
    if (!card) return;
    
    card.classList.remove('dragging');
    
    const deltaX = currentX - startX;
    const deltaY = currentY - startY;
    const cardContent = card.querySelector('.card-content');
    
    // Determine swipe action
    let swipeAction = null;
    if (deltaY < -100) {
        swipeAction = 'super_like';
    } else if (deltaX > 100) {
        swipeAction = 'like';
    } else if (deltaX < -100) {
        swipeAction = 'pass';
    }
    
    if (swipeAction) {
        animateCardExit(cardContent, swipeAction);
        processSwipe(swipeAction);
    } else {
        // Snap back to center
        cardContent.style.transform = '';
        cardContent.style.opacity = '';
        cardContent.querySelectorAll('.swipe-indicator').forEach(indicator => 
            indicator.classList.remove('show')
        );
    }
}

// Animate card exit
function animateCardExit(cardContent, action) {
    cardContent.classList.add(`swipe-${action === 'super_like' ? 'up' : action === 'like' ? 'right' : 'left'}`);
    
    setTimeout(() => {
        const card = cardContent.closest('.swipe-card');
        if (card) {
            card.remove();
            nextCard();
        }
    }, 300);
}

// Process swipe action
function processSwipe(action) {
    if (currentCardIndex >= currentCards.length) return;
    
    const currentCard = currentCards[currentCardIndex];
    const userType = document.body.dataset.userType || 'customer';
    
    // Send swipe action to server
    fetch('/api/swipe/action', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            action: action,
            target_id: currentCard.id,
            context_type: userType === 'customer' ? 'contractor_search' : 'job_application',
            context_id: currentCard.context_id || null
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success && data.match) {
            showMatchOverlay(data.match_data);
        }
        updateMatchCount(data.total_matches || 0);
    })
    .catch(error => {
        console.error('Error processing swipe:', error);
    });
}

// Move to next card
function nextCard() {
    currentCardIndex++;
    
    if (currentCardIndex >= currentCards.length) {
        // Load more cards if available
        loadMoreCards();
    } else {
        // Add new card to the stack
        const container = document.getElementById('swipeContainer');
        const existingCards = container.querySelectorAll('.swipe-card');
        
        if (existingCards.length < 3 && currentCardIndex + existingCards.length < currentCards.length) {
            const newCardIndex = currentCardIndex + existingCards.length;
            const newCard = createCardElement(currentCards[newCardIndex], existingCards.length);
            container.appendChild(newCard);
        }
        
        // Setup events for the new top card
        const topCard = container.querySelector('.swipe-card');
        if (topCard) {
            setupCardEvents(topCard);
        }
    }
}

// Programmatic swipe (from buttons)
function swipeCard(action) {
    const topCard = document.querySelector('.swipe-card .card-content');
    if (!topCard) return;
    
    animateCardExit(topCard, action);
    processSwipe(action);
}

// Show match overlay
function showMatchOverlay(matchData) {
    window.currentMatch = matchData;
    const overlay = document.getElementById('matchOverlay');
    const details = document.getElementById('matchDetails');
    
    const userType = document.body.dataset.userType || 'customer';
    const name = userType === 'customer' ? 
        matchData.business_name || matchData.contact_name :
        matchData.title;
    
    details.innerHTML = `
        <div class="flex items-center justify-center space-x-4 mb-4">
            <div class="w-20 h-20 bg-gradient-to-br from-blue-500 to-purple-500 rounded-full flex items-center justify-center">
                <i class="fas fa-${userType === 'customer' ? 'hard-hat' : 'briefcase'} text-white text-2xl"></i>
            </div>
            <div class="text-4xl">💕</div>
            <div class="w-20 h-20 bg-gradient-to-br from-green-500 to-blue-500 rounded-full flex items-center justify-center">
                <i class="fas fa-user text-white text-2xl"></i>
            </div>
        </div>
        <p class="text-lg text-gray-600">You and <strong>${name}</strong> liked each other!</p>
        <p class="text-sm text-gray-500 mt-2">Start a conversation to get things moving.</p>
    `;
    
    overlay.style.display = 'flex';
}

// Load more cards
function loadMoreCards() {
    if (currentCardIndex >= currentCards.length) {
        const userType = document.body.dataset.userType || 'customer';
        const endpoint = userType === 'customer' ? '/api/swipe/contractors' : '/api/swipe/jobs';
        
        fetch(endpoint, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                ...getFilterParams(),
                offset: currentCards.length
            })
        })
        .then(response => response.json())
        .then(data => {
            if (data.success && data.cards.length > 0) {
                currentCards = [...currentCards, ...data.cards];
                renderCards();
            } else {
                showNoMoreCards();
            }
        })
        .catch(error => {
            console.error('Error loading more cards:', error);
            showNoMoreCards();
        });
    }
}

// Show no more cards message
function showNoMoreCards() {
    document.getElementById('swipeContainer').style.display = 'none';
    document.getElementById('noMoreCards').classList.remove('hidden');
    document.querySelector('.swipe-actions').style.display = 'none';
}

// Get current filter parameters
function getFilterParams() {
    return {
        location: document.getElementById('locationFilter')?.value || '',
        service: document.getElementById('serviceFilter')?.value || '',
        min_rating: document.getElementById('ratingFilter')?.value || ''
    };
}

// Apply filters and reload cards
function applyFilters() {
    currentCards = [];
    currentCardIndex = 0;
    document.getElementById('swipeContainer').innerHTML = '<div id="loadingSpinner" class="text-center py-20"><div class="inline-block animate-spin rounded-full h-16 w-16 border-b-2 border-blue-600"></div><p class="mt-4 text-gray-600">Loading potential matches...</p></div>';
    document.getElementById('noMoreCards').classList.add('hidden');
    document.querySelector('.swipe-actions').style.display = 'flex';
    
    loadInitialCards();
    toggleFilters();
}

// Update match count
function updateMatchCount(count) {
    document.getElementById('matchCount').textContent = count;
}

// Setup keyboard shortcuts
function setupKeyboardEvents() {
    document.addEventListener('keydown', function(e) {
        if (e.target.tagName.toLowerCase() === 'input') return;
        
        switch(e.key) {
            case 'ArrowLeft':
                e.preventDefault();
                swipeCard('pass');
                break;
            case 'ArrowRight':
                e.preventDefault();
                swipeCard('like');
                break;
            case 'ArrowUp':
                e.preventDefault();
                swipeCard('super_like');
                break;
        }
    });
}

// Show error message
function showError(message) {
    const container = document.getElementById('swipeContainer');
    container.innerHTML = `
        <div class="text-center py-20">
            <i class="fas fa-exclamation-triangle text-6xl text-red-500 mb-4"></i>
            <h3 class="text-xl font-bold text-gray-800 mb-2">Oops!</h3>
            <p class="text-gray-600 mb-6">${message}</p>
            <button onclick="loadInitialCards()" class="bg-blue-600 text-white px-6 py-3 rounded-lg hover:bg-blue-700">
                Try Again
            </button>
        </div>
    `;
}