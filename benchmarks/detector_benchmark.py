"""Benchmark suite для AI-детектора TextHumanize.

Тестирует точность детекции на размеченных AI/human текстах.
Запуск: python benchmarks/detector_benchmark.py
"""

from __future__ import annotations

import sys
import time
from dataclasses import dataclass

sys.path.insert(0, ".")

from texthumanize.detectors import detect_ai

# ═══════════════════════════════════════════════════════════════
#  BENCHMARK DATASET
# ═══════════════════════════════════════════════════════════════

@dataclass
class Sample:
    text: str
    label: str   # "ai", "human", "mixed"
    lang: str
    source: str  # Description


SAMPLES: list[Sample] = [
    # ═══════════════════════════════════════════════════════════
    #  EN AI SAMPLES (30 samples)
    # ═══════════════════════════════════════════════════════════

    # 1
    Sample(
        text=(
            "Artificial intelligence has fundamentally transformed the landscape of modern technology. "
            "The implementation of machine learning algorithms has enabled unprecedented levels of automation "
            "and efficiency across various industries. Furthermore, the integration of natural language processing "
            "has revolutionized how we interact with digital systems. This comprehensive approach has yielded "
            "significant improvements in productivity and user experience. Moreover, the continuous advancement "
            "of deep learning architectures has opened new possibilities for solving complex problems. "
            "In addition, the ethical considerations surrounding AI deployment have become increasingly important. "
            "The development of responsible AI frameworks ensures that these technologies are utilized in a manner "
            "that benefits society as a whole. Consequently, organizations are investing substantial resources "
            "in AI research and development to maintain competitive advantage."
        ),
        label="ai", lang="en",
        source="ChatGPT generic tech essay",
    ),
    # 2
    Sample(
        text=(
            "The utilization of comprehensive methodologies in data analysis facilitates the identification "
            "of key patterns and trends. It is important to note that the implementation of robust statistical "
            "frameworks enables researchers to draw meaningful conclusions from complex datasets. Furthermore, "
            "the application of advanced visualization techniques enhances the interpretability of results. "
            "Additionally, the integration of machine learning models with traditional statistical methods "
            "provides a holistic approach to data-driven decision making. In conclusion, the systematic "
            "application of these methodologies ensures the reliability and validity of research findings."
        ),
        label="ai", lang="en",
        source="ChatGPT academic style",
    ),
    # 3
    Sample(
        text=(
            "In today's rapidly evolving digital landscape, organizations must leverage cutting-edge "
            "technologies to stay competitive. The strategic implementation of cloud computing solutions "
            "enables businesses to scale their operations efficiently. Moreover, the adoption of agile "
            "methodologies has transformed project management practices across industries. This paradigm "
            "shift has resulted in improved collaboration, faster delivery cycles, and enhanced product "
            "quality. Furthermore, the emergence of DevOps practices has bridged the gap between development "
            "and operations teams, fostering a culture of continuous improvement."
        ),
        label="ai", lang="en",
        source="ChatGPT business/tech blog",
    ),
    # 4
    Sample(
        text=(
            "Climate change represents one of the most pressing challenges facing humanity today. "
            "The scientific consensus is clear: anthropogenic greenhouse gas emissions are the primary "
            "driver of global warming. Rising temperatures have led to unprecedented changes in weather "
            "patterns, sea levels, and biodiversity. It is crucial that governments, corporations, and "
            "individuals take immediate action to mitigate these effects. The implementation of renewable "
            "energy solutions, such as solar and wind power, offers a viable pathway toward a sustainable "
            "future. Furthermore, the adoption of circular economy principles can significantly reduce "
            "waste and resource consumption. In conclusion, addressing climate change requires a "
            "comprehensive, multi-stakeholder approach that balances economic growth with environmental "
            "stewardship."
        ),
        label="ai", lang="en",
        source="ChatGPT climate essay",
    ),
    # 5
    Sample(
        text=(
            "The importance of mental health awareness cannot be overstated in contemporary society. "
            "Psychological well-being is a fundamental component of overall health, yet it remains "
            "significantly undervalued in many cultures. The stigma surrounding mental health conditions "
            "often prevents individuals from seeking the help they need. It is essential to foster open "
            "dialogue about mental health and to provide accessible resources for those who are struggling. "
            "Moreover, the integration of mental health services into primary healthcare systems can "
            "help bridge the gap between physical and psychological treatment. Educational institutions "
            "also play a crucial role in promoting mental health literacy among young people."
        ),
        label="ai", lang="en",
        source="ChatGPT health/wellness essay",
    ),
    # 6
    Sample(
        text=(
            "Blockchain technology has emerged as a transformative force in the financial sector. "
            "The decentralized nature of blockchain networks provides unprecedented transparency "
            "and security for financial transactions. Smart contracts enable automated execution "
            "of agreements without intermediaries, reducing costs and increasing efficiency. "
            "Furthermore, the tokenization of assets opens new possibilities for fractional "
            "ownership and democratized investment. However, regulatory challenges remain a "
            "significant hurdle to widespread adoption. The development of comprehensive "
            "regulatory frameworks is essential to harness the full potential of this technology "
            "while protecting consumers and maintaining financial stability."
        ),
        label="ai", lang="en",
        source="ChatGPT fintech article",
    ),
    # 7
    Sample(
        text=(
            "Effective leadership in the modern workplace requires a multifaceted approach that "
            "combines emotional intelligence with strategic thinking. Leaders must be able to "
            "inspire and motivate their teams while navigating complex organizational dynamics. "
            "The cultivation of a positive work culture is essential for employee retention and "
            "productivity. Moreover, embracing diversity and inclusion creates a more innovative "
            "and resilient workforce. Transformational leaders understand that empowering their "
            "team members leads to better outcomes than micromanagement. In addition, continuous "
            "professional development ensures that leaders remain adaptable in an ever-changing "
            "business environment."
        ),
        label="ai", lang="en",
        source="ChatGPT leadership article",
    ),
    # 8
    Sample(
        text=(
            "The evolution of cybersecurity threats necessitates a proactive approach to digital "
            "defense. Organizations must implement multi-layered security strategies that encompass "
            "network monitoring, endpoint protection, and employee training. The rise of sophisticated "
            "attack vectors, including ransomware and advanced persistent threats, underscores the "
            "importance of staying ahead of malicious actors. Furthermore, the adoption of zero-trust "
            "architecture provides a robust framework for minimizing potential vulnerabilities. "
            "Regular security audits and penetration testing are essential components of a comprehensive "
            "cybersecurity posture. Ultimately, the protection of sensitive data requires ongoing "
            "vigilance and investment in cutting-edge security technologies."
        ),
        label="ai", lang="en",
        source="ChatGPT cybersecurity article",
    ),
    # 9
    Sample(
        text=(
            "Sustainable agriculture represents a critical pathway toward ensuring global food "
            "security while preserving environmental resources. The integration of precision "
            "farming technologies enables farmers to optimize resource utilization and minimize "
            "waste. Crop rotation, cover cropping, and integrated pest management are fundamental "
            "practices that enhance soil health and biodiversity. Moreover, the development of "
            "drought-resistant crop varieties through genetic research offers promising solutions "
            "to the challenges posed by climate change. It is imperative that agricultural policies "
            "support the transition toward more sustainable practices while ensuring the economic "
            "viability of farming communities."
        ),
        label="ai", lang="en",
        source="ChatGPT agriculture essay",
    ),
    # 10
    Sample(
        text=(
            "The democratization of education through online learning platforms has revolutionized "
            "access to knowledge worldwide. Massive open online courses enable learners from diverse "
            "backgrounds to acquire new skills and credentials at their own pace. The integration of "
            "interactive elements, such as virtual labs and peer-to-peer discussion forums, enhances "
            "the learning experience. Additionally, adaptive learning algorithms personalize educational "
            "content to meet individual needs. However, challenges such as the digital divide, "
            "credential recognition, and maintaining student engagement must be addressed to fully "
            "realize the potential of online education."
        ),
        label="ai", lang="en",
        source="ChatGPT education article",
    ),
    # 11
    Sample(
        text=(
            "Remote work has fundamentally reshaped the modern workplace, offering both opportunities "
            "and challenges for organizations and employees alike. The flexibility of working from home "
            "has improved work-life balance for many professionals. However, the absence of face-to-face "
            "interaction can lead to feelings of isolation and hinder collaboration. Organizations must "
            "invest in robust communication tools and establish clear expectations to maximize productivity "
            "in remote settings. Furthermore, the creation of virtual team-building activities can help "
            "maintain a sense of community among distributed teams. Ultimately, a hybrid model that "
            "combines remote and in-office work may offer the best of both worlds."
        ),
        label="ai", lang="en",
        source="ChatGPT remote work article",
    ),
    # 12
    Sample(
        text=(
            "The advent of quantum computing promises to revolutionize computational capabilities "
            "across numerous domains. Unlike classical computers that process information in binary "
            "states, quantum computers leverage the principles of superposition and entanglement to "
            "perform calculations at unprecedented speeds. This technology holds particular promise "
            "for cryptography, drug discovery, and optimization problems that are currently intractable. "
            "However, significant technical challenges, including qubit stability and error correction, "
            "must be overcome before quantum computing can achieve widespread practical application. "
            "The ongoing collaboration between academia, industry, and government agencies is essential "
            "to advancing this transformative technology."
        ),
        label="ai", lang="en",
        source="ChatGPT quantum computing",
    ),
    # 13 — Claude-style (more nuanced, hedging)
    Sample(
        text=(
            "It's worth noting that the relationship between social media usage and mental health "
            "is more nuanced than often portrayed. While several studies have found correlations "
            "between heavy social media use and increased rates of anxiety and depression, establishing "
            "direct causation remains challenging. The effects likely vary significantly based on "
            "individual factors, including age, personality traits, and the specific ways in which "
            "platforms are used. Passive consumption of curated content may have different psychological "
            "impacts compared to active engagement and community building. A balanced perspective "
            "acknowledges both the potential harms and the genuine benefits that social media can "
            "provide, particularly for marginalized communities seeking connection and support."
        ),
        label="ai", lang="en",
        source="Claude-style nuanced essay",
    ),
    # 14 — GPT-4 style (structured, authoritative)
    Sample(
        text=(
            "The integration of artificial intelligence into healthcare diagnostics represents a "
            "watershed moment in medical practice. Current AI systems demonstrate remarkable accuracy "
            "in identifying patterns within medical imaging, often matching or exceeding the performance "
            "of experienced radiologists. These systems excel particularly in detecting early-stage "
            "cancers, retinal diseases, and cardiovascular conditions. The scalability of such solutions "
            "has the potential to address critical shortages in specialist availability, particularly "
            "in underserved regions. Nevertheless, the implementation of AI diagnostics requires "
            "careful consideration of regulatory frameworks, liability structures, and the fundamental "
            "importance of maintaining the physician-patient relationship as a cornerstone of effective "
            "healthcare delivery."
        ),
        label="ai", lang="en",
        source="GPT-4 medical article",
    ),
    # 15 — Gemini-style (conversational AI)
    Sample(
        text=(
            "Let's dive into the fascinating world of space exploration and what it means for humanity's "
            "future. The recent advancements in reusable rocket technology have dramatically reduced the "
            "cost of accessing space, opening doors that were previously closed to all but the wealthiest "
            "nations. Companies like SpaceX and Blue Origin are pushing boundaries, while international "
            "collaborations continue to yield valuable scientific discoveries. The prospect of establishing "
            "permanent human settlements on Mars is no longer science fiction — it's an engineering "
            "challenge that many believe can be solved within the coming decades. Of course, this raises "
            "important questions about planetary protection, resource allocation, and the governance of "
            "extraterrestrial territories."
        ),
        label="ai", lang="en",
        source="Gemini-style conversational",
    ),
    # 16
    Sample(
        text=(
            "The role of microbiome diversity in human health has become a subject of intense scientific "
            "inquiry. Research indicates that the gut microbiome influences not only digestive health "
            "but also immune function, mental health, and metabolic processes. The composition of microbial "
            "communities is shaped by diet, environment, medication use, and genetic factors. Probiotic "
            "supplementation and dietary interventions offer promising avenues for modulating the microbiome "
            "to improve health outcomes. However, the complexity of microbial ecosystems means that "
            "one-size-fits-all approaches are unlikely to be effective. Personalized interventions based "
            "on individual microbiome profiling represent the frontier of this rapidly evolving field."
        ),
        label="ai", lang="en",
        source="AI medical/health content",
    ),
    # 17
    Sample(
        text=(
            "Urban planning in the 21st century must prioritize sustainability, walkability, and "
            "equitable access to resources. The concept of the 15-minute city, where residents can "
            "access all essential services within a short walk or bike ride, has gained significant "
            "traction among planners worldwide. Green infrastructure, including urban forests, rain "
            "gardens, and permeable surfaces, mitigates the urban heat island effect and manages "
            "stormwater runoff. Transit-oriented development concentrates growth around public "
            "transportation hubs, reducing car dependency. The challenge lies in retrofitting "
            "existing cities while ensuring that sustainability improvements do not exacerbate "
            "gentrification and displacement of vulnerable communities."
        ),
        label="ai", lang="en",
        source="AI urban planning article",
    ),
    # 18 — marketing copy AI
    Sample(
        text=(
            "Transform your productivity with our revolutionary task management solution. Our "
            "platform seamlessly integrates with your existing workflow, enabling teams to "
            "collaborate more effectively than ever before. With cutting-edge AI-powered "
            "prioritization, you'll never miss a deadline again. Our intuitive interface "
            "ensures a minimal learning curve, while powerful analytics provide actionable "
            "insights into team performance. Join thousands of satisfied customers who have "
            "already experienced the transformative power of streamlined project management. "
            "Start your free trial today and discover why industry leaders trust our solution "
            "for their most critical projects."
        ),
        label="ai", lang="en",
        source="AI marketing copy",
    ),
    # 19 — AI legal/formal
    Sample(
        text=(
            "The aforementioned provisions shall be interpreted in accordance with the governing "
            "principles of international commercial law. Furthermore, any disputes arising from "
            "the interpretation or execution of this agreement shall be subject to binding "
            "arbitration under the rules of the International Chamber of Commerce. The parties "
            "hereby acknowledge and agree that the obligations set forth herein constitute "
            "binding commitments enforceable under applicable law. Moreover, any modification "
            "or amendment to this agreement must be executed in writing and signed by authorized "
            "representatives of both parties. The provisions of this document shall survive "
            "termination of the underlying contractual relationship."
        ),
        label="ai", lang="en",
        source="AI legal document",
    ),
    # 20 — AI creative writing
    Sample(
        text=(
            "The ancient library stood at the edge of the world, its towering spires reaching "
            "toward a sky painted in shades of amber and crimson. Within its hallowed halls, "
            "countless volumes chronicled the history of civilizations long forgotten. The air "
            "was thick with the scent of aged parchment and the whisper of knowledge waiting "
            "to be discovered. A young scholar named Elara navigated the labyrinthine corridors, "
            "her footsteps echoing against marble floors that had witnessed the passage of "
            "millennia. She sought the legendary Codex of Shadows, a tome said to contain the "
            "secrets of reality itself. As she ventured deeper, the flickering torchlight cast "
            "dancing shadows that seemed to beckon her forward into the unknown."
        ),
        label="ai", lang="en",
        source="AI creative/fantasy writing",
    ),
    # 21 — AI email
    Sample(
        text=(
            "Dear Team, I hope this email finds you well. I wanted to take a moment to provide "
            "an update on our Q3 progress and outline the key priorities for the upcoming quarter. "
            "First and foremost, I am pleased to report that we have exceeded our revenue targets "
            "by 15%, which is a testament to the hard work and dedication of everyone on this team. "
            "Moving forward, our primary focus will be on three strategic initiatives: expanding our "
            "market presence in the Asia-Pacific region, launching the redesigned customer portal, "
            "and implementing the new performance management framework. I would like to schedule a "
            "team meeting next week to discuss these priorities in detail. Please let me know your "
            "availability. Best regards."
        ),
        label="ai", lang="en",
        source="AI corporate email",
    ),
    # 22 — AI recipe/how-to
    Sample(
        text=(
            "Creating the perfect sourdough bread requires patience, precision, and an understanding "
            "of the fermentation process. Begin by combining 500 grams of bread flour with 350 grams "
            "of water and 100 grams of active sourdough starter. Mix until a shaggy dough forms, "
            "then allow it to rest for 30 minutes in a process known as autolyse. Next, incorporate "
            "10 grams of salt and perform a series of stretch-and-fold techniques every 30 minutes "
            "for the first two hours. The dough should develop a smooth, elastic texture with visible "
            "air bubbles. After a total bulk fermentation of 8-10 hours at room temperature, shape "
            "the dough and transfer it to a proofing basket. Refrigerate overnight for optimal flavor "
            "development, then bake in a preheated Dutch oven at 450°F for 45 minutes."
        ),
        label="ai", lang="en",
        source="AI recipe/instructional",
    ),
    # 23 — AI product review
    Sample(
        text=(
            "The latest flagship smartphone from TechCorp delivers an impressive combination of "
            "performance, camera quality, and battery life. The device features a stunning 6.7-inch "
            "AMOLED display with a 120Hz refresh rate that provides buttery-smooth scrolling and "
            "vibrant color reproduction. Under the hood, the proprietary T9 chipset handles demanding "
            "tasks with remarkable efficiency, ensuring seamless multitasking and gaming performance. "
            "The triple-camera system, featuring a 200MP main sensor, produces exceptionally detailed "
            "photographs in various lighting conditions. Battery life is equally impressive, with the "
            "5500mAh cell easily lasting a full day of heavy use. Overall, this device represents "
            "a compelling option for users seeking a premium smartphone experience."
        ),
        label="ai", lang="en",
        source="AI product review",
    ),
    # 24 — AI travel article
    Sample(
        text=(
            "Barcelona is a city that seamlessly blends rich historical heritage with contemporary "
            "vibrancy. The iconic Sagrada Familia, Antoni Gaudí's masterpiece, continues to captivate "
            "visitors with its awe-inspiring architecture and intricate facades. Beyond its architectural "
            "marvels, Barcelona offers a culinary scene that rivals any in Europe, from traditional "
            "tapas bars in the Gothic Quarter to Michelin-starred restaurants along the waterfront. "
            "The city's beaches provide a welcome respite from urban exploration, while the vibrant "
            "nightlife scene in neighborhoods like El Born ensures that entertainment extends well "
            "into the early hours. Whether you're a history enthusiast, a food lover, or simply "
            "seeking a memorable Mediterranean experience, Barcelona delivers on every front."
        ),
        label="ai", lang="en",
        source="AI travel article",
    ),
    # 25 — AI news-style
    Sample(
        text=(
            "Global leaders convened at the International Climate Summit on Monday to address the "
            "escalating crisis of environmental degradation. The summit, attended by representatives "
            "from over 150 nations, focused on establishing concrete benchmarks for carbon emission "
            "reductions by 2030. Key proposals included the establishment of a global carbon pricing "
            "mechanism, increased investment in renewable energy infrastructure, and the creation of "
            "a dedicated fund to support developing nations in their transition to sustainable energy "
            "sources. While significant progress was made in preliminary negotiations, several major "
            "emitting countries expressed reservations about the proposed timeline, citing potential "
            "economic disruptions. The summit is expected to conclude with a formal declaration "
            "outlining shared commitments and accountability measures."
        ),
        label="ai", lang="en",
        source="AI news article",
    ),
    # 26 — AI philosophical essay
    Sample(
        text=(
            "The concept of free will has been a subject of philosophical debate for millennia, "
            "and recent advances in neuroscience have added new dimensions to this discussion. "
            "Deterministic perspectives argue that every human decision is the inevitable result "
            "of prior causes, rendering the notion of genuine choice an illusion. Compatibilists, "
            "however, maintain that free will is compatible with determinism, provided we define "
            "freedom as the ability to act according to one's desires without external coercion. "
            "The implications of this debate extend far beyond academic philosophy, touching upon "
            "fundamental questions of moral responsibility, justice, and the very nature of human "
            "agency. As our understanding of neural processes deepens, society will increasingly "
            "need to grapple with these profound questions."
        ),
        label="ai", lang="en",
        source="AI philosophy essay",
    ),
    # 27 — Claude-style (systematic)
    Sample(
        text=(
            "When considering the impact of automation on employment, it's important to examine "
            "the evidence with nuance rather than defaulting to either utopian or dystopian narratives. "
            "Historically, technological disruptions have indeed eliminated certain categories of jobs "
            "while simultaneously creating new ones. The cotton gin displaced manual laborers but "
            "expanded the textile industry. Similarly, ATMs didn't eliminate bank teller positions; "
            "they actually shifted tellers toward more complex customer service roles. That said, "
            "the current wave of AI-driven automation may differ in important ways from previous "
            "technological transitions. The speed and breadth of disruption, coupled with AI's "
            "increasing capability in cognitive tasks previously thought to be exclusively human "
            "domains, suggests that without thoughtful policy interventions, the transition could "
            "be significantly more disruptive than historical precedents."
        ),
        label="ai", lang="en",
        source="Claude-style analytical",
    ),
    # 28 — AI self-help
    Sample(
        text=(
            "Building resilience is essential for navigating the challenges and uncertainties of "
            "modern life. Resilient individuals possess the ability to adapt to adversity, maintain "
            "a positive outlook, and emerge stronger from difficult experiences. Cultivating resilience "
            "begins with developing a growth mindset — the belief that challenges are opportunities "
            "for learning rather than insurmountable obstacles. Establishing strong social connections, "
            "practicing mindfulness, and maintaining physical health are all foundational components "
            "of a resilient lifestyle. Additionally, setting realistic goals and celebrating small "
            "victories helps build confidence and momentum. Remember, resilience is not an innate "
            "trait but a skill that can be developed through intentional practice and self-reflection."
        ),
        label="ai", lang="en",
        source="AI self-help content",
    ),
    # 29 — AI code documentation
    Sample(
        text=(
            "The authentication module provides a comprehensive set of utilities for managing user "
            "sessions and access control. The primary function, authenticate_user, accepts a username "
            "and password combination, validates the credentials against the database, and returns a "
            "JSON Web Token upon successful authentication. The token includes the user's role and "
            "permissions, enabling fine-grained access control throughout the application. Additionally, "
            "the module implements rate limiting to prevent brute-force attacks and supports multi-factor "
            "authentication for enhanced security. Error handling follows the standard pattern of "
            "returning appropriate HTTP status codes with descriptive error messages. For detailed "
            "usage examples and configuration options, please refer to the API reference documentation."
        ),
        label="ai", lang="en",
        source="AI technical documentation",
    ),
    # 30 — AI listicle-style
    Sample(
        text=(
            "Maintaining a healthy work-life balance is crucial for long-term professional success "
            "and personal well-being. Establishing clear boundaries between work and personal time "
            "prevents burnout and promotes sustained productivity. Regular physical exercise not only "
            "improves physical health but also enhances cognitive function and emotional regulation. "
            "Prioritizing quality sleep ensures optimal mental performance and decision-making "
            "capability throughout the day. Cultivating hobbies and interests outside of work "
            "provides a sense of fulfillment and perspective. Finally, nurturing meaningful "
            "relationships with family and friends creates a support network that sustains us "
            "through both professional challenges and personal difficulties."
        ),
        label="ai", lang="en",
        source="AI wellness listicle",
    ),

    # ═══════════════════════════════════════════════════════════
    #  EN HUMAN SAMPLES (30 samples)
    # ═══════════════════════════════════════════════════════════

    # 31
    Sample(
        text=(
            "So I was trying to fix my bike yesterday and man, what a mess. The chain kept slipping "
            "off every time I pedaled uphill. I watched like three YouTube videos about it and they all "
            "said different things. Eventually I just took it to the shop down the street -- the guy there "
            "is pretty chill and doesn't charge much. Turns out the derailleur was bent. Who knew? "
            "He fixed it in about 20 minutes. Cost me fifteen bucks. Not bad honestly."
        ),
        label="human", lang="en",
        source="Casual blog/forum post",
    ),
    # 32
    Sample(
        text=(
            "Look, I've been coding for about fifteen years now, and here's what I've learned: "
            "the perfect architecture doesn't exist. You can spend months planning... or you can "
            "just start building and refactor later. Both approaches have tradeoffs. "
            "Most of the code I wrote in my first five years is terrible by today's standards, "
            "but it worked. And that's what mattered. The users didn't care about my code structure. "
            "They cared about whether the button did what they expected when they clicked it. "
            "Sometimes I think we overthink this stuff."
        ),
        label="human", lang="en",
        source="Developer blog (informal, reflective)",
    ),
    # 33
    Sample(
        text=(
            "The expedition to K2 in 1953 was nothing short of extraordinary. "
            "We'd been stuck at Camp III for two days due to weather. When the storm broke, "
            "Amir and I decided to push for Camp IV despite the risks. The snow was waist-deep "
            "in places and the wind — God, the wind. It tore at us like something alive. "
            "At one point I lost feeling in my left hand for about an hour. Frightening. "
            "But we made it. The view from 25,000 feet... words fail me, honestly."
        ),
        label="human", lang="en",
        source="Memoir/narrative prose",
    ),
    # 34
    Sample(
        text=(
            "my cat threw up on my keyboard at 3am and somehow mass-replied to every email in "
            "my inbox. woke up to 47 confused responses from coworkers. one of them said 'great "
            "point about agshdjfk, can we discuss in standup?' I am never recovering from this. "
            "honestly debating whether to explain or just let them think im having a stroke"
        ),
        label="human", lang="en",
        source="Twitter/social media post",
    ),
    # 35
    Sample(
        text=(
            "The thing about depression nobody tells you is how boring it is. Like yeah it's "
            "sad and whatever but mostly it's just... boring. You sit there. You know you should "
            "do things. You don't do them. You watch the same show for the fourth time because "
            "starting something new feels like climbing Everest. Then you feel guilty about "
            "wasting time. Then you're too tired to feel guilty. It's a whole cycle."
        ),
        label="human", lang="en",
        source="Reddit personal essay",
    ),
    # 36
    Sample(
        text=(
            "OK so here's the deal with sourdough — everyone makes it sound way harder than it "
            "is. You literally mix flour and water and wait. That's it. My first loaf looked "
            "like a frisbee and tasted like cardboard but by the third one I was getting actual "
            "oven spring. The secret? Don't mess with the dough too much. I mean it. Stop "
            "poking it. Also your kitchen is probably too cold. Put it near the oven or on "
            "top of your fridge. Trust me on this."
        ),
        label="human", lang="en",
        source="Casual cooking blog",
    ),
    # 37
    Sample(
        text=(
            "Drove through west Texas last week. Nothing for miles except scrub brush and wind "
            "turbines turning slow against a washed-out sky. Stopped at this roadside diner "
            "outside Pecos — just a counter, six stools, and a woman named Darlene who's been "
            "running the place since '89. She makes a green chile burger that's worth the detour. "
            "We talked about the drought, her grandson in the Marines, the cost of propane. "
            "Sometimes the best conversations happen in the emptiest places."
        ),
        label="human", lang="en",
        source="Travel blog/personal essay",
    ),
    # 38
    Sample(
        text=(
            "I don't understand why everyone's panicking about AI taking our jobs. Like, have "
            "you tried asking ChatGPT to do anything complicated? I asked it to write a bash "
            "script to rename files and it gave me something that would've deleted my entire "
            "home directory. Three times. Different prompts, same result. We're safe for now "
            "lol. Maybe in ten years. But right now? Nah."
        ),
        label="human", lang="en",
        source="Forum post / HN comment",
    ),
    # 39
    Sample(
        text=(
            "Jan's MRI came back and it's not great. The tumor hasn't grown but it hasn't "
            "shrunk either. Dr. Patel is suggesting we try a different protocol — something "
            "newer, more targeted. Insurance is fighting us on it, naturally. I spent three "
            "hours on the phone yesterday getting bounced between departments. Nobody knows "
            "anything. It's exhausting being a patient in this system. We'll figure it out. "
            "We always do. But man, some days are harder than others."
        ),
        label="human", lang="en",
        source="Personal health journal",
    ),
    # 40
    Sample(
        text=(
            "Reviewed the manuscript for Nature Genetics — it's solid work but the stats are "
            "a mess. They're using a t-test on what's clearly non-normal data, the sample size "
            "for the control group is n=4 (!!!), and the error bars in Figure 3 are unlabeled. "
            "Are those SEM or SD? Makes a huge difference. Wrote a detailed review, tried to be "
            "constructive. Recommended major revisions. Probably won't make me popular with the "
            "authors but that's not really the point."
        ),
        label="human", lang="en",
        source="Academic peer review notes",
    ),
    # 41
    Sample(
        text=(
            "You know what's wild about teaching high school? Every year the kids change but the "
            "problems don't. Phones in class. Missing homework. The kid who sleeps through third "
            "period every single day. But then — then there's the moment when something clicks. "
            "Yesterday, Marcus — quiet kid, back row, never talks — he raised his hand and asked "
            "this incredibly insightful question about the French Revolution. Like genuinely "
            "thoughtful. The whole room went silent. Those moments make the rest worth it."
        ),
        label="human", lang="en",
        source="Teacher's blog",
    ),
    # 42
    Sample(
        text=(
            "Listing: 3BR/2BA ranch style, 1,847 sqft on a half acre. Needs work — roof is "
            "original (1978), kitchen hasn't been updated since the Clinton administration, "
            "and there's a crack in the foundation wall in the basement that the seller says "
            "is 'cosmetic.' Sure, Bob. HVAC was replaced in 2019, that's the one bright spot. "
            "Good bones though. Location is solid — two blocks from the elementary school, "
            "quiet street. Listed at $285K, worth maybe $260. Let me know if you want to see it."
        ),
        label="human", lang="en",
        source="Realtor notes/email",
    ),
    # 43
    Sample(
        text=(
            "Here's the thing I wish someone told me before I started my business: the first "
            "year is going to suck. No sugarcoating it. You'll work more hours than any 9-to-5 "
            "for less money than minimum wage. Your friends will stop inviting you to things. "
            "Your partner will start sentences with 'I feel like you're always...' But if you "
            "survive year one — and maybe even year two — something shifts. You get your first "
            "repeat client. You figure out what doesn't work. You stop saying yes to everything. "
            "That's when it starts getting good."
        ),
        label="human", lang="en",
        source="Entrepreneur blog",
    ),
    # 44
    Sample(
        text=(
            "Standing at the cemetery in the rain. Mom's stone is already starting to show its "
            "age — been seven years now. The flowers I brought last time are dried husks. Changed "
            "them out. Stood there for a while not knowing what to say. Funny how you can talk "
            "to someone every day for thirty years and then when they're gone you can't think of "
            "a single word. Told her about the grandkids. She'd have loved them. She'd have "
            "spoiled them rotten. That thought made me smile."
        ),
        label="human", lang="en",
        source="Personal journal/memoir",
    ),
    # 45
    Sample(
        text=(
            "DEBUG: spent 6 hours tracking down a memory leak in the websocket handler. The "
            "connection pool wasn't properly releasing connections when clients disconnected "
            "abnormally. The fix was literally one line — adding a try/finally around the "
            "handler coroutine. ONE LINE. Six hours. I'm going to bed. Also note to future "
            "me: the metrics dashboard is lying. It shows 200 active connections but conntrack "
            "shows 12,000. Something in the prometheus exporter is wrong. Fix tomorrow."
        ),
        label="human", lang="en",
        source="Developer log/notes",
    ),
    # 46
    Sample(
        text=(
            "Got back from the farmers market with way too much produce again. Three pounds of "
            "tomatoes, bunch of basil, some weird squash I've never seen before — the vendor "
            "called it a 'costata romanesco' or something? It's got ridges. Pretty. No idea "
            "how to cook it. Texted mom and she said to slice it thin and grill it with olive "
            "oil. We'll see. Also got some gorgeous peaches. Ate two on the walk home."
        ),
        label="human", lang="en",
        source="Personal blog / slice of life",
    ),
    # 47
    Sample(
        text=(
            "The witness stated that he observed the defendant's vehicle traveling westbound on "
            "Highway 42 at approximately 10:45 PM. He described the vehicle as a dark-colored "
            "pickup truck, possibly a Ford F-150, traveling at what he estimated to be 'well over "
            "eighty.' Traffic was light. When asked how he could estimate the speed, he stated "
            "that he's 'been driving that road for twenty years' and 'you can tell.' Not exactly "
            "scientific but the jury seemed to buy it."
        ),
        label="human", lang="en",
        source="Legal case notes",
    ),
    # 48
    Sample(
        text=(
            "Three things I learned from failing at marathon training twice: First, you can't "
            "jump from couch to 26.2 in twelve weeks no matter what that app says. Second, "
            "rest days aren't optional — my ITB didn't care about my training schedule. Third, "
            "nutrition matters more than pace. I bonked at mile 18 in my first attempt because "
            "I thought a granola bar and some Gatorade would cut it. Spoiler: it did not. "
            "Starting over with a 20-week plan this time. We'll see."
        ),
        label="human", lang="en",
        source="Running / fitness blog",
    ),
    # 49
    Sample(
        text=(
            "I hated Ulysses the first time I read it. Hated it. Couldn't get past page 80. "
            "Tried again five years later and something had changed — maybe I had. The Proteus "
            "chapter on Sandymount Strand suddenly made sense. Not logical sense, but the kind "
            "that happens when you stop trying to understand and just let it wash over you. "
            "Joyce wasn't writing a novel. He was composing music. Once I heard it that way, "
            "I couldn't unhear it."
        ),
        label="human", lang="en",
        source="Book review / personal essay",
    ),
    # 50
    Sample(
        text=(
            "Patient presents with 3-day history of progressive dyspnea, productive cough with "
            "yellowish sputum. Temp 38.7°C, HR 102, BP 118/74, SpO2 93\u0025 on RA. Right lower lobe "
            "crackles on auscultation. CXR shows right lower lobe consolidation. WBC 14.2, CRP 87. "
            "Assessment: community-acquired pneumonia. Plan: start amoxicillin-clavulanate 875/125 "
            "BID x 7 days, follow up 48-72h, return if worsening SOB or fever."
        ),
        label="human", lang="en",
        source="Clinical notes / SOAP",
    ),
    # 51 — human academic
    Sample(
        text=(
            "Our results suggest — tentatively — that the observed correlation between screen time "
            "and sleep disruption may be partially mediated by blue light exposure, though the "
            "effect size was smaller than we anticipated (d = 0.23, p = .041). It's possible "
            "that behavioral factors (staying up to finish one more episode) play a larger role "
            "than the physiological mechanism itself. We should note that our sample skewed "
            "heavily toward university students, which limits generalizability. Future work "
            "with a more diverse age range would help clarify these preliminary findings."
        ),
        label="human", lang="en",
        source="Academic paper discussion section",
    ),
    # 52
    Sample(
        text=(
            "Honestly the best pizza I've ever had was at this hole-in-the-wall place in New "
            "Haven. Di Zingara or something — can't remember the exact name. No ambiance. "
            "Plastic chairs, fluorescent lights, took 45 minutes for a pie. But my god... the "
            "crust had this char on it, thin as paper, and the sauce? Unreal. Sweet, bright, "
            "barely any cheese. My New York friends would disown me but it was better than "
            "literally any slice I've had in the city. Fight me."
        ),
        label="human", lang="en",
        source="Food blog / casual review",
    ),
    # 53
    Sample(
        text=(
            "The garage sale was a bust. Sat out there for six hours and made $42. Forty-two "
            "dollars. I priced everything so cheaply too — books for a quarter, clothes for a "
            "buck. Nobody wanted the furniture. An older couple looked at the dining set but "
            "said they'd 'think about it.' They're not coming back. At least the kids had fun "
            "running the 'lemonade stand' (which was really just Kool-Aid and a cardboard sign). "
            "They made more money than I did."
        ),
        label="human", lang="en",
        source="Personal journal",
    ),
    # 54
    Sample(
        text=(
            "I swear to god if one more person tells me to 'just exercise more' for my anxiety "
            "I'm going to scream. Yes Karen I'm aware that running releases endorphins. You know "
            "what else it releases? My knee pain. And also the feeling of being watched by "
            "everyone in the park. And also the panic that I'm going to die of a heart attack. "
            "But sure. Let me just go for a jog. That'll fix the generalized doom."
        ),
        label="human", lang="en",
        source="Reddit rant / social media",
    ),
    # 55
    Sample(
        text=(
            "The meeting with the Hendrix account didn't go great. They want a full rebrand "
            "by March which is insane — we haven't even finished the brand audit. Sarah pitched "
            "the color palette and they loved the teal but want to 'explore something warmer.' "
            "I think they mean orange. Everyone always means orange. We're presenting revised "
            "concepts next Thursday. Also Mike is out all next week for his wedding so I'm "
            "handling his accounts too. Fun times."
        ),
        label="human", lang="en",
        source="Work email / internal notes",
    ),
    # 56
    Sample(
        text=(
            "We pulled the boat out at first light, just me and my old man. Fog was sitting "
            "low on the lake — couldn't see more than fifty yards. He didn't say much. Never "
            "does these days. We fished for three hours and caught nothing. On the way back he "
            "pointed at a heron standing in the shallows and said 'there's dinner.' I laughed "
            "harder than I have in months. It's not about the fish. It was never about the fish."
        ),
        label="human", lang="en",
        source="Personal narrative",
    ),
    # 57
    Sample(
        text=(
            "To be honest I'm not sure typescript generics are worth the complexity they add in "
            "most projects. Like yeah, if you're writing a library, absolutely. But for your "
            "average CRUD app? You're spending more time fighting the type system than writing "
            "features. I've seen 200-line type definitions that could've been replaced with a "
            "simple interface and a type assertion. But try saying that on Twitter and the TS "
            "zealots come for you. Anyway, that's my hot take for today."
        ),
        label="human", lang="en",
        source="Dev blog hot take",
    ),
    # 58
    Sample(
        text=(
            "Rent in this city has officially lost its mind. Saw a listing today: 400 sqft studio, "
            "no dishwasher, next to a highway on-ramp, and they want $2,100/month. The photos "
            "showed the toilet basically IN the kitchen. Like, you could stir pasta while on the "
            "john. And it had 30 applications already. Thirty. We are cooked."
        ),
        label="human", lang="en",
        source="Social media rant",
    ),
    # 59
    Sample(
        text=(
            "Grandma called today. She wanted to know if I'd 'figured out the computers yet' — "
            "I've been a software engineer for twelve years. She also asked if I could fix her "
            "printer. Again. It's not even plugged in. It's never plugged in. But I said yes "
            "because she said she'd make pierogi if I came over. Some things are worth an hour "
            "on the floor behind a desk trying to reach a power outlet from 1987."
        ),
        label="human", lang="en",
        source="Personal anecdote / blog",
    ),
    # 60
    Sample(
        text=(
            "We lost the game 4-3 in overtime. I'm still processing it. Martinez had an open "
            "look with ten seconds left and just... missed. Not his fault, really — the pass was "
            "behind him and he had to adjust. But still. We outplayed them for three quarters. "
            "Our defense was the best it's been all season. Coach didn't say much after. Just "
            "told us to hold our heads up. Not sure I can yet."
        ),
        label="human", lang="en",
        source="Sports commentary / journal",
    ),

    # ═══════════════════════════════════════════════════════════
    #  RU AI SAMPLES (20 samples)
    # ═══════════════════════════════════════════════════════════

    # 61
    Sample(
        text=(
            "Искусственный интеллект представляет собой одно из наиболее значимых достижений "
            "современной науки и технологий. Внедрение алгоритмов машинного обучения позволило "
            "автоматизировать множество процессов, которые ранее требовали значительных "
            "человеческих ресурсов. Более того, развитие нейронных сетей открыло новые "
            "перспективы в области обработки естественного языка. Таким образом, данная "
            "технология оказывает существенное влияние на различные сферы деятельности. "
            "В заключение следует отметить, что ответственное применение ИИ является "
            "ключевым фактором успешной цифровой трансформации."
        ),
        label="ai", lang="ru",
        source="ChatGPT русский формальный",
    ),
    # 62
    Sample(
        text=(
            "В рамках данного исследования был проведён комплексный анализ эффективности "
            "различных методов обработки текстовых данных. Результаты показали, что "
            "применение современных алгоритмов обеспечивает значительное повышение "
            "точности классификации. Кроме того, использование предобученных языковых "
            "моделей способствует улучшению качества генерации текста. Необходимо "
            "подчеркнуть, что дальнейшие исследования в данном направлении представляются "
            "весьма перспективными."
        ),
        label="ai", lang="ru",
        source="ChatGPT русский академический",
    ),
    # 63
    Sample(
        text=(
            "Здоровый образ жизни является ключевым фактором поддержания физического и "
            "психического благополучия. Регулярные физические упражнения способствуют "
            "укреплению сердечно-сосудистой системы, улучшению обмена веществ и повышению "
            "общего тонуса организма. Сбалансированное питание обеспечивает организм "
            "необходимыми витаминами и микроэлементами. Кроме того, полноценный сон "
            "играет важнейшую роль в процессах восстановления и регенерации. Следует "
            "отметить, что комплексный подход к здоровью, включающий как физическую "
            "активность, так и ментальное благополучие, является наиболее эффективным."
        ),
        label="ai", lang="ru",
        source="ChatGPT ЗОЖ статья",
    ),
    # 64
    Sample(
        text=(
            "Современная система образования переживает период значительной трансформации, "
            "обусловленной развитием цифровых технологий. Внедрение дистанционного обучения "
            "открыло новые возможности для получения знаний вне зависимости от географического "
            "расположения учащихся. Интерактивные образовательные платформы обеспечивают "
            "индивидуализированный подход к каждому студенту. Вместе с тем, цифровизация "
            "образования сопряжена с определёнными вызовами, включая необходимость "
            "обеспечения равного доступа к технологиям и поддержания качества образовательного "
            "процесса. Таким образом, успешная модернизация системы образования требует "
            "сбалансированного сочетания традиционных и инновационных методов обучения."
        ),
        label="ai", lang="ru",
        source="ChatGPT образование",
    ),
    # 65
    Sample(
        text=(
            "Экологическая обстановка в мире требует незамедлительного принятия решительных мер "
            "на всех уровнях — от индивидуального до глобального. Загрязнение атмосферы, "
            "истощение природных ресурсов и утрата биоразнообразия представляют серьёзные угрозы "
            "для устойчивого развития человечества. Переход на возобновляемые источники энергии, "
            "развитие экономики замкнутого цикла и ужесточение экологического законодательства "
            "являются приоритетными направлениями в борьбе с изменением климата. Важно "
            "подчеркнуть, что каждый человек может внести свой вклад в решение экологических "
            "проблем посредством осознанного потребления и ответственного отношения к природе."
        ),
        label="ai", lang="ru",
        source="ChatGPT экология",
    ),
    # 66
    Sample(
        text=(
            "Цифровая трансформация бизнеса стала неотъемлемым условием конкурентоспособности "
            "в современной экономике. Компании, успешно интегрирующие цифровые технологии в "
            "свои бизнес-процессы, демонстрируют значительное преимущество перед конкурентами. "
            "Автоматизация рутинных операций позволяет сократить издержки и повысить "
            "эффективность работы. Аналитика больших данных предоставляет возможности для "
            "принятия обоснованных стратегических решений. Вместе с тем, цифровая трансформация "
            "требует значительных инвестиций и изменения корпоративной культуры."
        ),
        label="ai", lang="ru",
        source="ChatGPT бизнес",
    ),
    # 67
    Sample(
        text=(
            "Кибербезопасность приобретает всё большее значение в условиях стремительной "
            "цифровизации общества. Киберугрозы становятся более изощрёнными и масштабными, "
            "что требует постоянного совершенствования систем защиты информации. Организациям "
            "необходимо внедрять многоуровневые стратегии безопасности, включающие технические "
            "средства защиты, обучение персонала и регулярный аудит информационных систем. "
            "Применение принципов нулевого доверия и шифрования данных является фундаментальным "
            "элементом современной кибербезопасности."
        ),
        label="ai", lang="ru",
        source="ChatGPT кибербезопасность",
    ),
    # 68
    Sample(
        text=(
            "Развитие квантовых вычислений представляет собой одно из наиболее перспективных "
            "направлений современной информатики. Квантовые компьютеры обладают потенциалом "
            "для решения задач, которые классические вычислительные системы не способны "
            "обработать за приемлемое время. Области применения квантовых технологий включают "
            "криптографию, моделирование молекулярных структур и оптимизационные задачи. "
            "Однако создание стабильных кубитов и устранение квантовых ошибок остаются "
            "ключевыми техническими вызовами. Тем не менее, значительные инвестиции ведущих "
            "технологических компаний свидетельствуют о высоком потенциале данного направления."
        ),
        label="ai", lang="ru",
        source="ChatGPT квантовые компьютеры",
    ),
    # 69
    Sample(
        text=(
            "Блокчейн-технология, изначально разработанная для обеспечения функционирования "
            "криптовалют, сегодня находит применение в самых различных отраслях. Децентрализованная "
            "природа блокчейна обеспечивает беспрецедентный уровень прозрачности и безопасности "
            "транзакций. Смарт-контракты позволяют автоматизировать исполнение договорных "
            "обязательств без посредников. Токенизация активов открывает новые возможности "
            "для инвестирования. Вместе с тем, масштабируемость, энергопотребление и "
            "регуляторная неопределённость остаются значительными препятствиями для массового "
            "внедрения данной технологии."
        ),
        label="ai", lang="ru",
        source="ChatGPT блокчейн",
    ),
    # 70
    Sample(
        text=(
            "Космические исследования продолжают расширять границы человеческого познания. "
            "Последние достижения в области ракетостроения, в частности развитие многоразовых "
            "ракет-носителей, существенно снизили стоимость доступа в космос. Исследование "
            "Марса остаётся приоритетным направлением для ведущих космических агентств. "
            "Международная кооперация в космической области способствует обмену научными "
            "данными и технологиями. Перспектива создания постоянных поселений на других "
            "планетах из области научной фантастики постепенно переходит в сферу реальных "
            "инженерных задач."
        ),
        label="ai", lang="ru",
        source="ChatGPT космос",
    ),
    # 71
    Sample(
        text=(
            "Важно отметить, что процесс урбанизации оказывает значительное влияние на все "
            "аспекты жизни общества. Рост городского населения создаёт новые вызовы в сфере "
            "инфраструктуры, транспорта и экологии. Концепция умного города предлагает "
            "инновационные решения данных проблем посредством интеграции цифровых технологий "
            "в управление городской средой. Умные системы управления трафиком, энергоэффективные "
            "здания и цифровые сервисы для граждан — всё это составляющие города будущего. "
            "Тем не менее, реализация подобных проектов требует значительных финансовых "
            "вложений и стратегического планирования."
        ),
        label="ai", lang="ru",
        source="ChatGPT урбанистика",
    ),
    # 72
    Sample(
        text=(
            "Роль искусства в формировании общественного сознания трудно переоценить. "
            "На протяжении всей истории человечества художественное творчество служило "
            "средством самовыражения, социальной критики и культурной идентификации. "
            "Современное искусство расширяет традиционные границы, используя новые "
            "медиа и технологии для создания иммерсивных переживаний. Взаимодействие "
            "искусства и технологий порождает новые формы творческого выражения, такие "
            "как генеративное искусство и виртуальные инсталляции. В то же время "
            "остаётся актуальным вопрос о границах между подлинным творчеством и "
            "машинной генерацией контента."
        ),
        label="ai", lang="ru",
        source="ChatGPT культура/искусство",
    ),
    # 73
    Sample(
        text=(
            "Правильное питание является основой здоровья и долголетия. Сбалансированный "
            "рацион должен включать достаточное количество белков, жиров и углеводов, а также "
            "необходимые витамины и минералы. Следует отдавать предпочтение натуральным и "
            "минимально обработанным продуктам. Важно соблюдать режим питания и избегать "
            "чрезмерного потребления сахара и трансжиров. Кроме того, индивидуальный подход "
            "к составлению рациона, учитывающий возраст, уровень физической активности и "
            "состояние здоровья, является наиболее эффективным. Консультация диетолога "
            "поможет определить оптимальный план питания."
        ),
        label="ai", lang="ru",
        source="ChatGPT диетология",
    ),
    # 74
    Sample(
        text=(
            "Электромобили представляют собой будущее автомобильной промышленности. "
            "Развитие аккумуляторных технологий значительно увеличило запас хода "
            "электрических транспортных средств. Расширение инфраструктуры зарядных "
            "станций делает электромобили всё более практичным выбором для повседневного "
            "использования. Снижение стоимости производства батарей способствует "
            "повышению доступности электрических автомобилей для широкого круга потребителей. "
            "Переход на электрический транспорт является важным шагом в направлении "
            "снижения углеродного следа и борьбы с загрязнением воздуха."
        ),
        label="ai", lang="ru",
        source="ChatGPT электромобили",
    ),
    # 75
    Sample(
        text=(
            "Психологическое благополучие и ментальное здоровье являются важнейшими "
            "компонентами качества жизни современного человека. Стрессы, связанные с "
            "ускоренным темпом жизни и информационной перегрузкой, оказывают негативное "
            "влияние на психическое состояние. Практики осознанности и медитации "
            "демонстрируют высокую эффективность в управлении стрессом. Когнитивно-"
            "поведенческая терапия является одним из наиболее научно обоснованных "
            "методов лечения тревожных расстройств и депрессии. Важно подчеркнуть "
            "необходимость снижения стигматизации обращения за психологической помощью."
        ),
        label="ai", lang="ru",
        source="ChatGPT психология",
    ),
    # 76
    Sample(
        text=(
            "Стоит подчеркнуть, что развитие сектора возобновляемой энергетики "
            "набирает обороты по всему миру. Солнечная и ветровая энергия становятся "
            "экономически конкурентоспособными по сравнению с традиционными ископаемыми "
            "источниками. Инвестиции в зелёные технологии открывают новые рабочие "
            "места и способствуют экономическому росту. Вместе с тем, проблемы "
            "хранения энергии и стабильности электросетей требуют инновационных "
            "решений. Международное сотрудничество в области энергетического перехода "
            "является необходимым условием достижения климатических целей."
        ),
        label="ai", lang="ru",
        source="ChatGPT энергетика",
    ),
    # 77
    Sample(
        text=(
            "Нейросети глубокого обучения совершили революцию в обработке изображений. "
            "Свёрточные нейронные сети способны распознавать объекты с точностью, "
            "превосходящей человеческие возможности. Генеративные состязательные сети "
            "позволяют создавать реалистичные изображения, что нашло применение в "
            "индустрии развлечений, дизайне и медицине. Однако этические вопросы, "
            "связанные с технологией дипфейков, вызывают обоснованную обеспокоенность "
            "общества. Разработка механизмов выявления сгенерированного контента "
            "становится приоритетной задачей для исследователей."
        ),
        label="ai", lang="ru",
        source="ChatGPT нейросети",
    ),
    # 78
    Sample(
        text=(
            "Туризм играет значительную роль в экономике многих стран мира. "
            "Развитие транспортной инфраструктуры и появление бюджетных авиалиний "
            "сделали путешествия доступными для широких слоёв населения. Культурный "
            "и экологический туризм способствуют сохранению природного и исторического "
            "наследия. Вместе с тем, массовый туризм создаёт серьёзные проблемы "
            "для популярных направлений, включая деградацию окружающей среды и "
            "перегрузку инфраструктуры. Устойчивый туризм предлагает альтернативный "
            "подход, минимизирующий негативное воздействие на экологию и местные "
            "сообщества."
        ),
        label="ai", lang="ru",
        source="ChatGPT туризм",
    ),
    # 79
    Sample(
        text=(
            "На сегодняшний день робототехника является одной из наиболее динамично "
            "развивающихся отраслей науки и промышленности. Промышленные роботы уже "
            "давно стали неотъемлемой частью производственных процессов, обеспечивая "
            "высокую точность и производительность. Сервисные роботы находят всё "
            "более широкое применение в медицине, логистике и бытовой сфере. "
            "Развитие искусственного интеллекта наделяет роботов способностью "
            "адаптироваться к изменяющимся условиям и принимать самостоятельные "
            "решения. Социальные и этические аспекты роботизации заслуживают "
            "пристального внимания общества."
        ),
        label="ai", lang="ru",
        source="ChatGPT робототехника",
    ),
    # 80
    Sample(
        text=(
            "Геополитическая обстановка в мире претерпевает существенные изменения. "
            "Многополярность становится определяющей характеристикой современных "
            "международных отношений. Экономическое соперничество между крупнейшими "
            "державами влияет на глобальные торговые потоки и инвестиционные стратегии. "
            "Региональные интеграционные объединения играют всё более заметную роль "
            "в мировой политике. Вызовы глобальной безопасности, включая терроризм, "
            "кибервойны и пандемии, требуют координированных международных усилий."
        ),
        label="ai", lang="ru",
        source="ChatGPT геополитика",
    ),

    # ═══════════════════════════════════════════════════════════
    #  RU HUMAN SAMPLES (20 samples)
    # ═══════════════════════════════════════════════════════════

    # 81
    Sample(
        text=(
            "Вчера полдня провозился с настройкой сервера. Казалось бы — поставь nginx, "
            "прокинь конфиг и готово. Ага, щас. Сначала сертификат не хотел обновляться, "
            "потом оказалось что порт 443 занят каким-то левым процессом. Убил час на поиск "
            "причины. В итоге — забытый docker-контейнер от прошлого проекта. Классика. "
            "Ну хоть разобрался. Заодно обнёс настройки и сделал бэкап на всякий случай."
        ),
        label="human", lang="ru",
        source="IT-блог / Хабр разговорный",
    ),
    # 82
    Sample(
        text=(
            "Знаете, что бесит в современных приложениях? Подписки. На всё подписки. "
            "Раньше купил программу — и пользуйся. А сейчас? Хочешь Excel — подписка. "
            "Хочешь Photoshop — подписка. Даже блокнот какой-нибудь — и тот за доллар в месяц. "
            "И ладно бы качество росло. Так нет же, те же баги, тот же интерфейс. "
            "Просто деньги стригут. Ладно, пойду open source поищу..."
        ),
        label="human", lang="ru",
        source="Пост в соцсетях / форуме",
    ),
    # 83
    Sample(
        text=(
            "Варил борщ по маминому рецепту. Ну как по маминому — мама в рецепт буряка кладёт "
            "'сколько не жалко' и мясо 'какое на рынке было'. Попробовал угадать пропорции. "
            "Буряк переложил, слишком сладкий вышел. Зато цвет — космос, прям рубиновый. "
            "Батя попробовал, сказал 'ну... мама лучше делает'. Спасибо, пап. Очень мотивирует."
        ),
        label="human", lang="ru",
        source="Кулинарный блог разговорный",
    ),
    # 84
    Sample(
        text=(
            "Поехали в поход на Алтай. Планировали пять дней, вернулись через три. Дождь "
            "лил безостановочно, палатку протекла в первую же ночь. Серёга умудрился "
            "утопить рюкзак при переправе через ручей. В рюкзаке были спальник, документы "
            "и вся сухая одежда. Мы ржали как кони, потом мёрзли как собаки. Зато шашлык "
            "на мокрых дровах — это отдельный вид искусства. Будем ли ездить ещё? Конечно. "
            "Мы ж идиоты."
        ),
        label="human", lang="ru",
        source="Тревел-блог неформальный",
    ),
    # 85
    Sample(
        text=(
            "Сегодня на митинге менеджер сказал 'давайте думать out of the box' и я чуть "
            "не подавилась кофе. Потом был 'we need to leverage synergies' и 'let's circle "
            "back on that'. За час собрания я услышала больше англицизмов чем за неделю "
            "просмотра Netflix. И всё это — на совещании по продаже удобрений. УДОБРЕНИЙ. "
            "Какой out of the box, Антон? Навоз есть навоз."
        ),
        label="human", lang="ru",
        source="Корпоративная сатира",
    ),
    # 86
    Sample(
        text=(
            "Мне 42 и я только сейчас начинаю понимать, что тогда имела в виду бабушка. "
            "Она говорила: 'не гонись за всем сразу'. Я думал — ну, банальность. "
            "А потом посмотрел на свою жизнь: три незаконченных курса, два брошенных хобби, "
            "работа которая не нравится но привык, и квартира в ипотеку на 25 лет. "
            "Вот тебе и 'не гонись'. Правда в том, что я так боялся выбрать что-то одно, "
            "что выбрал ничего."
        ),
        label="human", lang="ru",
        source="Личный блог / рефлексия",
    ),
    # 87
    Sample(
        text=(
            "Собеседование прошло странно. Парень из HR спрашивал про мои 'hard skills', "
            "а сам путал Java и JavaScript. Потом техлид полчаса допрашивал про алгоритмы, "
            "которые я ни разу не использовал за 8 лет работы. Перевернуть бинарное дерево? "
            "Серьёзно? Я бэкенд пишу, не олимпиады решаю. В конце сказали 'мы вам перезвоним'. "
            "Не перезвонили. И ладно."
        ),
        label="human", lang="ru",
        source="IT-форум / rant",
    ),
    # 88
    Sample(
        text=(
            "Утро начинается одинаково: кофе, сигарета, взгляд в окно. За окном — стройка, "
            "которую обещали закончить ещё два года назад. Кран стоит. Рабочих нет. Забор из "
            "профнастила облез и покосился. По вечерам подростки лазят через дыру и жгут "
            "костры. Написали в управу — ответ пришёл через месяц, общие слова ни о чём. "
            "Типичная история, короче. Привыкли."
        ),
        label="human", lang="ru",
        source="Городской блог",
    ),
    # 89
    Sample(
        text=(
            "Дочке шесть. Спрашивает: 'Пап, а почему небо голубое?' Я такой — отлично, "
            "расскажу про рассеяние Рэлея, блесну интеллектом. Начинаю объяснять, она "
            "перебивает: 'А почему у Барсика хвост полосатый?' Не дожидаясь ответа: "
            " 'А пираты существуют?' — 'А мороженое из чего?' — 'А ты когда-нибудь умрёшь?' "
            "Вот так за минуту от оптики до экзистенциального кризиса."
        ),
        label="human", lang="ru",
        source="Родительский блог",
    ),
    # 90
    Sample(
        text=(
            "Работаю в скорой восемь лет. Каждый день — как русская рулетка. Сегодня "
            "бабушка с давлением 240, завтра ДТП на кольцевой. На прошлой неделе вызвали "
            "к мужику — 'болит живот'. Приехали — аппендицит, причём уже перитонит начинался. "
            "Еле довезли. Хирург потом сказал — ещё час и всё. А мужик неделю терпел. Неделю! "
            "'Думал само пройдёт.' Я таких историй могу тысячу рассказать."
        ),
        label="human", lang="ru",
        source="Профессиональный блог врача",
    ),
    # 91
    Sample(
        text=(
            "Купил наконец новый ноут. Переезжал со старого, и знаете что? На старом "
            "было 847 гигов фоток, из которых я отсортировал может штук 200. Остальное — "
            "три копии одного и того же, скриншоты из 2018-го и почему-то фото чека из "
            "Пятёрочки от марта 2021. Зачем я это сохранил? Кто этот человек? "
            "Ладно, скинул всё на внешний диск и назвал папку 'разберу потом'. Не разберу."
        ),
        label="human", lang="ru",
        source="IT-юмор / личный блог",
    ),
    # 92
    Sample(
        text=(
            "Ремонт в квартире — это стихийное бедствие, растянутое во времени. Мы 'ненадолго' "
            "начали менять обои в спальне. Это было в августе. Сейчас ноябрь, мы живём на кухне, "
            "половина стен голый бетон, а плиточник пропал, забрав аванс. Жена молчит, но я "
            "вижу по глазам — она планирует моё убийство. Зато выбрали светильники. Красивые. "
            "Вешать некуда, но красивые."
        ),
        label="human", lang="ru",
        source="Бытовой юмор / форум",
    ),
    # 93
    Sample(
        text=(
            "Отвёл пса к ветеринару. Той-терьер, пять кило мокрого весу, а трясётся так, "
            "будто его на допрос ведут. Ветеринар — девушка молодая, нежная — берёт его, "
            "а он от ужаса ей в руку вцепился. Ей больно, но она улыбается и говорит 'ничего "
            "страшного'. На обратном пути купил ему сосиску. Виноват, знаю. Но он так "
            "жалобно смотрел."
        ),
        label="human", lang="ru",
        source="Личная история / питомцы",
    ),
    # 94
    Sample(
        text=(
            "На работе ввели 'инновацию' — стоячие рабочие места. Ну то есть нам убрали стулья "
            "и поставили высокие столики. 'Для здоровья', говорит начальство. К обеду все сидят "
            "на подоконниках и перевёрнутых мусорках. Вася из бухгалтерии принёс свой стул "
            "из дома. Его пристыдили на летучке. Вася плевать хотел. Вася мой герой."
        ),
        label="human", lang="ru",
        source="Офисный быт",
    ),
    # 95
    Sample(
        text=(
            "Три часа ночи. Не спится. Мозг решил именно сейчас вспомнить все неловкие момент "
            "за последние двадцать лет. Вот я в седьмом классе падаю в столовой с подносом. "
            "Вот я на первом свидании зову официанта 'мам'. Вот я на собеседовании говорю "
            "'я вас тоже люблю' вместо 'до свидания'. Мозг, стоп. Пожалуйста."
        ),
        label="human", lang="ru",
        source="Бессонница / юмор",
    ),
    # 96
    Sample(
        text=(
            "Шли с друзьями по Невскому в минус 20. Нос не чувствую, пальцы на ногах тоже. "
            "Зашли в какую-то кофейню погреться. Кофе стоил 500 рублей. Пятьсот! За эспрессо! "
            "Но там было тепло. Сели, отогрелись. Бариста напутал и сделал нам двойную порцию. "
            "Не стал переделывать — 'забирайте так'. Питер, конечно, город контрастов."
        ),
        label="human", lang="ru",
        source="Тревел-блог Россия",
    ),
    # 97
    Sample(
        text=(
            "Завтра экзамен по матану. Я знаю три теоремы из двадцати. Одна из них — теорема "
            "Пифагора, и я не уверен что она вообще нужна на матане. Сижу перед учебником "
            "уже пять часов. За это время я успел: помыть чашку, реорганизовать рабочий стол, "
            "узнать столицу Буркина-Фасо (Уагадугу, если что) и посмотреть три видео про "
            "чёрные дыры. Учебник открыт на той же странице."
        ),
        label="human", lang="ru",
        source="Студенческий юмор",
    ),
    # 98
    Sample(
        text=(
            "Тёща приехала 'на денёк'. Это было три недели назад. Она переставила всю мебель "
            "на кухне. Жена говорит 'мама права, так удобнее'. Я теперь ищу вилки в ящике "
            "с полотенцами. Тарелки переехали на балкон. Почему? 'Там свет лучше.' Тарелкам "
            "нужен свет? С каких пор? Но я молчу. Молчание — основа крепкого брака."
        ),
        label="human", lang="ru",
        source="Семейный юмор",
    ),
    # 99
    Sample(
        text=(
            "Пациент, 67 лет, обратился повторно с жалобами на боли в правом подреберье. "
            "При пальпации — болезненность, печень +2 см от края рёберной дуги. УЗИ — "
            "диффузные изменения паренхимы, конкремент 12 мм в желчном. Рекомендовано: "
            "диета стол 5, но-шпа при болях, повторное УЗИ через месяц. Пациент спрашивает "
            "'а водку-то можно?' На мой взгляд, нельзя. Но он и так знает ответ."
        ),
        label="human", lang="ru",
        source="Медицинский блог / дневник",
    ),
    # 100
    Sample(
        text=(
            "Копал грядки у мамы на даче. Лопата старая, деревянная, рассохлась — и черенок "
            "с размаху отломился. Получил занозу в ладонь. Мама достала зелёнку, которая, "
            "судя по этикетке, была произведена ещё при Брежневе. Но работает. Зелёнка — она "
            "вечная. Как мамины огурцы — каждый год одни и те же, и каждый год вкуснейшие."
        ),
        label="human", lang="ru",
        source="Дачный блог",
    ),

    # ═══════════════════════════════════════════════════════════
    #  MIXED SAMPLES (10 samples)
    # ═══════════════════════════════════════════════════════════

    # 101
    Sample(
        text=(
            "Machine learning has become increasingly important in healthcare diagnostics. "
            "The algorithms can detect patterns that doctors might miss. That said, I've seen "
            "some pretty questionable results in practice — like when my hospital's system flagged "
            "a perfectly healthy patient as high-risk because of a data entry error. We need to "
            "be careful about blindly trusting these systems. The implementation of proper "
            "validation frameworks ensures reliability, but honestly, most facilities don't "
            "have the resources for that kind of thorough testing."
        ),
        label="mixed", lang="en",
        source="AI-generated with human edits",
    ),
    # 102
    Sample(
        text=(
            "The rapid advancement of renewable energy technologies has created unprecedented "
            "opportunities for sustainable development. Solar panel efficiency has increased "
            "dramatically over the past decade. I remember when my uncle tried installing panels "
            "back in 2008 — total disaster. The installer drilled through a water pipe and we "
            "spent the weekend mopping up the garage. But yeah, the technology has matured "
            "significantly, driven by increased investment and policy support."
        ),
        label="mixed", lang="en",
        source="AI intro + human anecdote",
    ),
    # 103
    Sample(
        text=(
            "So I asked ChatGPT to write my cover letter and here's what it gave me: "
            "'I am writing to express my enthusiastic interest in the Software Engineer position "
            "at your esteemed organization. With my comprehensive skill set and unwavering "
            "dedication to excellence, I am confident...' Yeah no. I rewrote the whole thing. "
            "Dear hiring manager, I can code, I show up on time, and I don't microwave fish "
            "in the office kitchen. Hire me."
        ),
        label="mixed", lang="en",
        source="Human framing + AI quote",
    ),
    # 104
    Sample(
        text=(
            "Python is an incredibly versatile programming language that has gained tremendous "
            "popularity across various domains. Its clean syntax and extensive library ecosystem "
            "make it suitable for web development, data science, and machine learning applications. "
            "tbh tho the GIL is still annoying as hell for CPU-bound stuff and don't get me "
            "started on the packaging situation. pip, poetry, conda, pdm — pick one and pray "
            "it works. The Python Enhancement Proposals provide a structured framework for "
            "evolving the language while maintaining backward compatibility."
        ),
        label="mixed", lang="en",
        source="AI paragraphs + human rant in middle",
    ),
    # 105
    Sample(
        text=(
            "Данная статья посвящена анализу современных тенденций в области мобильной "
            "разработки. Flutter и React Native являются наиболее популярными фреймворками "
            "для создания кроссплатформенных приложений. Хотя я лично после двух лет мучений "
            "с React Native перешёл на нативку и ни разу не пожалел. Да, дольше. Да, дороже. "
            "Зато работает нормально. Тем не менее, кроссплатформенная разработка обеспечивает "
            "значительную экономию ресурсов."
        ),
        label="mixed", lang="ru",
        source="AI + человеческая вставка",
    ),
    # 106
    Sample(
        text=(
            "Effective time management is essential for achieving both professional and personal "
            "goals. The Pomodoro Technique involves working in focused 25-minute intervals. "
            "honestly I tried it for a week and it just made me anxious watching the timer. "
            "like why am I racing against a tomato?? Prioritizing tasks using the Eisenhower "
            "Matrix helps distinguish between urgent and important activities, enabling more "
            "strategic allocation of time and resources."
        ),
        label="mixed", lang="en",
        source="AI advice + human reaction",
    ),
    # 107
    Sample(
        text=(
            "Искусственный интеллект активно внедряется в сферу образования. Адаптивные "
            "обучающие платформы позволяют подстраиваться под индивидуальный уровень каждого "
            "студента. Короче, я попробовал одну такую платформу — она мне неделю подряд "
            "показывала задачки на дроби, хотя я уже давно дифуры решаю. 'Адаптивная', ага. "
            "Тем не менее, потенциал данных технологий в образовании трудно переоценить."
        ),
        label="mixed", lang="ru",
        source="AI + разговорный comment",
    ),
    # 108
    Sample(
        text=(
            "The Mediterranean diet is widely regarded as one of the healthiest dietary patterns. "
            "Rich in olive oil, fish, and vegetables, it has been associated with reduced risk "
            "of cardiovascular disease. My nonna just called it 'eating normal food' and she lived "
            "to 96, so there's that. She'd roll over in her grave if she saw people spending $30 "
            "on 'Mediterranean bowls' at some trendy lunch spot. The emphasis on whole grains and "
            "lean proteins provides a balanced nutritional foundation."
        ),
        label="mixed", lang="en",
        source="AI health content + human family story",
    ),
    # 109
    Sample(
        text=(
            "The fundamentals of photography extend beyond technical knowledge of aperture, "
            "shutter speed, and ISO settings. Understanding light and composition transforms "
            "snapshots into compelling visual narratives. Ну вот честно — я купил камеру "
            "за сто тысяч и год снимал в авто-режиме. Потом наконец посмотрел один ютуб-ролик "
            "про экспозицию и у меня будто глаза открылись. Мог бы сразу. The journey of "
            "developing a unique photographic style is deeply personal and rewarding."
        ),
        label="mixed", lang="en",
        source="AI + RU human aside",
    ),
    # 110
    Sample(
        text=(
            "Современные методы управления проектами предусматривают использование гибких "
            "методологий разработки. Скрам-фреймворк обеспечивает итеративный подход к "
            "созданию продукта. Но если честно, у нас скрам выродился в то, что мы каждый "
            "день по 40 минут стоим на стендапе и обсуждаем кто что ел на обед. Ретроспектива — "
            "это когда все жалуются, а ничего не меняется. Тем не менее, правильно "
            "организованный скрам-процесс существенно повышает эффективность команды."
        ),
        label="mixed", lang="ru",
        source="AI + ироничный комментарий",
    ),
]


# ═══════════════════════════════════════════════════════════════
#  BENCHMARK RUNNER
# ═══════════════════════════════════════════════════════════════

def run_benchmark() -> None:
    """Запустить бенчмарк и показать результаты."""

    print("=" * 70)
    print("  TextHumanize AI Detector Benchmark")
    print(f"  Samples: {len(SAMPLES)}")
    print("=" * 70)
    print()

    correct = 0
    total = len(SAMPLES)
    results = []
    errors: list[str] = []

    total_time = 0.0

    for i, sample in enumerate(SAMPLES, 1):
        t0 = time.perf_counter()
        detection = detect_ai(sample.text, lang=sample.lang)
        elapsed = time.perf_counter() - t0
        total_time += elapsed

        predicted = detection.verdict
        is_correct = predicted == sample.label
        if is_correct:
            correct += 1

        status = "✓" if is_correct else "✗"
        results.append({
            "sample": i,
            "label": sample.label,
            "predicted": predicted,
            "score": detection.ai_probability,
            "confidence": detection.confidence,
            "correct": is_correct,
            "elapsed_ms": elapsed * 1000,
            "lang": sample.lang,
            "domain": getattr(detection, 'detected_domain', 'general'),
        })

        if not is_correct:
            errors.append(
                f"  ✗ #{i:3d} [{sample.lang.upper()}] "
                f"label={sample.label:6s} → {predicted:6s} "
                f"(score={detection.ai_probability:.1%}) "
                f"| {sample.source}"
            )

    # ── Summary ──
    accuracy = correct / total if total > 0 else 0
    avg_time = total_time / total * 1000 if total > 0 else 0

    print(f"  Overall Accuracy: {correct}/{total} = {accuracy:.1%}")
    print(f"  Avg time: {avg_time:.1f}ms per sample")
    print(f"  Total time: {total_time * 1000:.0f}ms")
    print()

    # ── Per-label breakdown ──
    print("─" * 70)
    print("  Per-label breakdown:")
    for label in ["ai", "human", "mixed"]:
        label_results = [r for r in results if r["label"] == label]
        if not label_results:
            continue
        label_correct = sum(1 for r in label_results if r["correct"])
        label_total = len(label_results)
        avg_score = sum(r["score"] for r in label_results) / label_total
        avg_conf = sum(r["confidence"] for r in label_results) / label_total
        label_acc = label_correct / label_total if label_total else 0
        print(
            f"    {label:6s}: {label_correct:2d}/{label_total:2d} = {label_acc:.0%}  "
            f"avg_score={avg_score:.1%}, avg_conf={avg_conf:.1%}"
        )

    # ── Per-language breakdown ──
    print()
    print("  Per-language breakdown:")
    for lang in sorted({r["lang"] for r in results}):
        lang_results = [r for r in results if r["lang"] == lang]
        lang_correct = sum(1 for r in lang_results if r["correct"])
        lang_total = len(lang_results)
        lang_acc = lang_correct / lang_total if lang_total else 0
        print(f"    {lang.upper():4s}: {lang_correct:2d}/{lang_total:2d} = {lang_acc:.0%}")

    # ── Errors ──
    if errors:
        print()
        print("─" * 70)
        print(f"  Misclassified ({len(errors)}):")
        for err in errors:
            print(err)

    # ── Detailed metrics for a few samples ──
    print()
    print("─" * 70)
    print("  Detailed metrics (Sample 1 = AI EN, Sample 31 = Human EN, Sample 61 = AI RU):")
    print()
    for idx in [0, 30, 60]:
        if idx >= len(SAMPLES):
            break
        sample = SAMPLES[idx]
        det = detect_ai(sample.text, lang=sample.lang)
        domain = getattr(det, 'detected_domain', '?')
        print(f"  [{sample.label.upper()}] {sample.source} [domain={domain}]")
        for metric, val in det.details.get("scores", {}).items():
            bar = "█" * int(val * 20) + "░" * (20 - int(val * 20))
            print(f"    {metric:14s} {bar} {val:.2f}")
        print()

    print("=" * 70)

    # Return exit code based on accuracy threshold
    if accuracy < 0.7:
        print("  ⚠ Accuracy below 70% threshold!")
        sys.exit(1)
    else:
        print(f"  ✓ Benchmark passed! ({accuracy:.1%})")


if __name__ == "__main__":
    run_benchmark()
